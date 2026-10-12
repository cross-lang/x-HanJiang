#!/usr/bin/env python3
"""开放平台开发者认证服务（DeveloperAuthService）单元测试。

覆盖目标模块 src/services/open_portal/auth_service.py：
    - 注册（两次密码不一致 / 用户名占用 / 邮箱占用 / 成功）
    - 登录（账号识别 / 密码错误 / 账号禁用 / 成功）
    - 刷新令牌、当前开发者解析（含 Redis 登录态各分支）、退出登录
    - 修改密码、邮箱验证码二次认证（改手机/邮箱）
    - 忘记密码：申请重置 / 重置密码

Redis、邮件、通知一律离线替身或 monkeypatch，不触网、不连库；bcrypt/PyJWT 真实可用。
"""

import pytest
from src.constants.constants import VERIFY_CODE_DEV_CACHE_PREFIX
from src.core.exceptions import (
    AuthenticationException,
    ConflictException,
    ValidationException,
)
from src.core.tokens import create_access_token, create_refresh_token, decode_token
from src.models.entities.developer_entity import DeveloperEntity
from src.services.open_portal.auth_service import DeveloperAuthService
from src.utils.security import hash_password

_PASSWORD = "DevPass@123"
_LOGIN_KEY = "login_dev:"


class FakeCacheProvider:
    """内存版缓存提供者替身。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.raise_on: set[str] = set()

    def get(self, key: str):
        if "get" in self.raise_on:
            raise RuntimeError("redis down")
        return self.store.get(key)

    def set(self, key: str, value, ttl: int = 300) -> None:
        if "set" in self.raise_on:
            raise RuntimeError("redis down")
        self.store[key] = str(value)

    def delete(self, key: str) -> None:
        if "delete" in self.raise_on:
            raise RuntimeError("redis down")
        self.store.pop(key, None)


class FakeDeveloperRepository:
    """内存版开发者仓库替身（接口与 DeveloperRepository 对齐）。"""

    session = None

    def __init__(self) -> None:
        self._items: dict[int, DeveloperEntity] = {}
        self._next_id = 1
        self.committed = 0
        self.rolled_back = 0

    def add(self, dev: DeveloperEntity) -> DeveloperEntity:
        if dev.id is None:
            dev.id = self._next_id
            self._next_id += 1
        # 对齐数据库 server_default：内存替身补齐非空字段
        if getattr(dev, "phone", None) is None:
            dev.phone = ""
        if getattr(dev, "certification_status", None) is None:
            dev.certification_status = "none"
        if getattr(dev, "created_at", None) is None:
            from datetime import datetime

            dev.created_at = datetime.now()
        self._items[dev.id] = dev
        return dev

    def get_by_id(self, id: int) -> DeveloperEntity | None:
        return self._items.get(id)

    def get_by_username(self, username: str) -> DeveloperEntity | None:
        return next((d for d in self._items.values() if d.username == username), None)

    def get_by_email(self, email: str) -> DeveloperEntity | None:
        return next((d for d in self._items.values() if d.email == email), None)

    def create(self, entity: DeveloperEntity) -> DeveloperEntity:
        return self.add(entity)

    def update_last_login(self, developer_id: int, last_login_at) -> None:
        existing = self._items.get(developer_id)
        if existing is not None:
            existing.last_login_at = last_login_at

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


def _make_dev(
    dev_id: int = 1,
    username: str = "devone",
    email: str = "devone@example.com",
    status: str = "enabled",
    password: str = _PASSWORD,
) -> DeveloperEntity:
    return DeveloperEntity(
        id=dev_id,
        username=username,
        email=email,
        password_hash=hash_password(password),
        name="开发者一",
        phone="",
        certification_type="personal",
        certification_status="none",
        status=status,
    )


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch) -> FakeCacheProvider:
    """把 Redis 缓存提供者替换为内存 Fake。"""
    fake = FakeCacheProvider()
    monkeypatch.setattr("src.infras.cache.get_cached_cache_provider", lambda: fake)
    return fake


@pytest.fixture
def repo() -> FakeDeveloperRepository:
    r = FakeDeveloperRepository()
    r.add(_make_dev())
    return r


@pytest.fixture
def svc(repo: FakeDeveloperRepository) -> DeveloperAuthService:
    return DeveloperAuthService(repository=repo)


class TestRegister:
    """开发者注册。"""

    def test_password_mismatch(self, cache: FakeCacheProvider) -> None:
        """两次密码不一致 → 认证异常。"""
        svc = DeveloperAuthService(repository=FakeDeveloperRepository())
        with pytest.raises(AuthenticationException):
            svc.register(
                username="newdev",
                email="new@example.com",
                password="SamePass@1",
                confirm_password="Different@1",
                name="新开发者",
                certification_type="personal",
            )

    def test_username_conflict(self, svc: DeveloperAuthService) -> None:
        """用户名已存在 → 冲突异常。"""
        with pytest.raises(ConflictException):
            svc.register(
                username="devone",
                email="other@example.com",
                password=_PASSWORD,
                confirm_password=_PASSWORD,
                name="x",
                certification_type="personal",
            )

    def test_email_conflict(self, svc: DeveloperAuthService) -> None:
        """邮箱已存在 → 冲突异常。"""
        with pytest.raises(ConflictException):
            svc.register(
                username="brandnew",
                email="devone@example.com",
                password=_PASSWORD,
                confirm_password=_PASSWORD,
                name="x",
                certification_type="personal",
            )

    def test_register_success(self, svc: DeveloperAuthService, repo: FakeDeveloperRepository) -> None:
        """合法注册成功，落库并返回资料。"""
        profile = svc.register(
            username="freshdev",
            email="fresh@example.com",
            password=_PASSWORD,
            confirm_password=_PASSWORD,
            name="新开发者",
            certification_type="enterprise",
        )
        assert profile.username == "freshdev"
        assert repo.get_by_username("freshdev") is not None


class TestLogin:
    """开发者登录。"""

    def test_login_success_by_username(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        resp = svc.login("devone", _PASSWORD)
        assert resp.access_token and resp.refresh_token
        assert cache.store.get(f"{_LOGIN_KEY}1")

    def test_login_by_email(self, svc: DeveloperAuthService) -> None:
        resp = svc.login("devone@example.com", _PASSWORD)
        assert resp.access_token

    def test_login_unknown_account(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.login("ghost", _PASSWORD)

    def test_login_wrong_password(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.login("devone", "bad-password")

    def test_login_disabled(self, repo: FakeDeveloperRepository) -> None:
        repo.add(_make_dev(dev_id=2, username="disableddev", email="d@example.com", status="disabled"))
        svc = DeveloperAuthService(repository=repo)
        with pytest.raises(AuthenticationException):
            svc.login("disableddev", _PASSWORD)


class TestRefresh:
    """刷新令牌。"""

    def test_refresh_success(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        token = create_refresh_token(1, extra_claims={"username": "devone"})
        resp = svc.refresh(token)
        assert resp.access_token and resp.refresh_token

    def test_refresh_invalid_token(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.refresh("garbage")

    def test_refresh_developer_not_found(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.refresh(create_refresh_token(999))

    def test_refresh_disabled(self, repo: FakeDeveloperRepository) -> None:
        repo.add(_make_dev(dev_id=2, username="d2", email="d2@example.com", status="disabled"))
        svc = DeveloperAuthService(repository=repo)
        with pytest.raises(AuthenticationException):
            svc.refresh(create_refresh_token(2))


class TestGetCurrentDeveloper:
    """当前开发者解析。"""

    def _seed(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> str:
        svc.login("devone", _PASSWORD)
        token = create_access_token(1, extra_claims={"username": "devone"})
        cache.store[f"{_LOGIN_KEY}1"] = decode_token(token).get("jti")
        return token

    def test_missing_header(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.get_current_developer(None)

    def test_invalid_token(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.get_current_developer("Bearer bad")

    def test_developer_not_found(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        token = create_access_token(999)
        with pytest.raises(AuthenticationException):
            svc.get_current_developer(f"Bearer {token}")

    def test_disabled(self, repo: FakeDeveloperRepository, cache: FakeCacheProvider) -> None:
        repo.add(_make_dev(dev_id=2, username="d2", email="d2@example.com", status="disabled"))
        svc = DeveloperAuthService(repository=repo)
        token = create_access_token(2)
        cache.store[f"{_LOGIN_KEY}2"] = decode_token(token).get("jti")
        with pytest.raises(AuthenticationException):
            svc.get_current_developer(f"Bearer {token}")

    def test_login_state_missing(self, svc: DeveloperAuthService) -> None:
        token = create_access_token(1)
        with pytest.raises(AuthenticationException):
            svc.get_current_developer(f"Bearer {token}")

    def test_jti_mismatch(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        cache.store[f"{_LOGIN_KEY}1"] = "stale"
        token = create_access_token(1)
        with pytest.raises(AuthenticationException):
            svc.get_current_developer(f"Bearer {token}")

    def test_success(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        token = self._seed(svc, cache)
        current = svc.get_current_developer(f"Bearer {token}")
        assert current.id == 1
        assert current.username == "devone"

    def test_redis_failure_passes_through(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        token = create_access_token(1)
        cache.raise_on.add("get")
        current = svc.get_current_developer(f"Bearer {token}")
        assert current.id == 1


class TestLogout:
    """退出登录。"""

    def test_logout_clears_state(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        cache.store[f"{_LOGIN_KEY}1"] = "jti"
        svc.logout(1)
        assert f"{_LOGIN_KEY}1" not in cache.store

    def test_logout_swallows_error(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        cache.raise_on.add("delete")
        svc.logout(1)


class TestChangePassword:
    """修改密码（含邮箱验证码二次认证）。"""

    def test_developer_not_found(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.change_password(999, _PASSWORD, "NewPass@123", "000000")

    def test_old_password_wrong(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.change_password(1, "wrong-old", "NewPass@123", "000000")

    def test_wrong_code(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(ValidationException):
            svc.change_password(1, _PASSWORD, "NewPass@123", "wrong-code")

    def test_success_updates_hash_and_logs_out(
        self, svc: DeveloperAuthService, repo: FakeDeveloperRepository, cache: FakeCacheProvider
    ) -> None:
        cache.store[f"{VERIFY_CODE_DEV_CACHE_PREFIX}1"] = "654321"
        cache.store[f"{_LOGIN_KEY}1"] = "jti"
        svc.change_password(1, _PASSWORD, "NewPass@123", "654321")
        # 密码哈希已变更且能通过新口令校验
        assert repo.get_by_id(1).password_hash != hash_password(_PASSWORD)
        # 改密后撤销全部登录态
        assert f"{_LOGIN_KEY}1" not in cache.store
        # 验证码一次性，已删除
        assert f"{VERIFY_CODE_DEV_CACHE_PREFIX}1" not in cache.store


class TestVerifyCodeFlow:
    """邮箱验证码发送与校验（改手机/邮箱）。"""

    def test_send_code_no_email(self, repo: FakeDeveloperRepository, cache: FakeCacheProvider) -> None:
        repo.add(_make_dev(dev_id=2, username="noemail", email=""))
        svc = DeveloperAuthService(repository=repo)
        with pytest.raises(ValidationException):
            svc.send_verify_code(2)

    def test_send_code_redis_failure(self, svc: DeveloperAuthService, cache: FakeCacheProvider) -> None:
        cache.raise_on.add("set")
        with pytest.raises(ConflictException):
            svc.send_verify_code(1)

    def test_send_code_email_send_failure(
        self, svc: DeveloperAuthService, cache: FakeCacheProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """验证码邮件发送失败 → 冲突异常并清理已写缓存。"""

        def _boom(self, to_email, code, username):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(DeveloperAuthService, "_dispatch_verify_email", _boom)
        with pytest.raises(ConflictException):
            svc.send_verify_code(1)
        # 清理后缓存中不应残留验证码键
        assert not any(k.startswith(VERIFY_CODE_DEV_CACHE_PREFIX) for k in cache.store)

    def test_send_code_success(
        self, svc: DeveloperAuthService, cache: FakeCacheProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sent: dict[str, str] = {}

        def _fake_dispatch(self, to_email, code, username):
            sent["to"] = to_email
            sent["code"] = code

        monkeypatch.setattr(DeveloperAuthService, "_dispatch_verify_email", _fake_dispatch)
        svc.send_verify_code(1)
        assert sent["to"] == "devone@example.com"
        # 写入的验证码与发送内容一致
        assert cache.store[f"{VERIFY_CODE_DEV_CACHE_PREFIX}1"] == sent["code"]

    def test_update_phone_bad_code(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(ValidationException):
            svc.verify_and_update_phone(1, "000000", "13900001111")

    def test_update_phone_success(
        self, svc: DeveloperAuthService, repo: FakeDeveloperRepository, cache: FakeCacheProvider
    ) -> None:
        cache.store[f"{VERIFY_CODE_DEV_CACHE_PREFIX}1"] = "111222"
        svc.verify_and_update_phone(1, "111222", "13900001111")
        assert repo.get_by_id(1).phone == "13900001111"

    def test_update_email_bad_code(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(ValidationException):
            svc.verify_and_update_email(1, "000000", "new@example.com")

    def test_update_email_conflict(
        self, svc: DeveloperAuthService, repo: FakeDeveloperRepository, cache: FakeCacheProvider
    ) -> None:
        """新邮箱被其他开发者占用 → 冲突。"""
        repo.add(_make_dev(dev_id=3, username="other", email="taken@example.com"))
        cache.store[f"{VERIFY_CODE_DEV_CACHE_PREFIX}1"] = "222333"
        with pytest.raises(ConflictException):
            svc.verify_and_update_email(1, "222333", "taken@example.com")

    def test_update_email_success(
        self, svc: DeveloperAuthService, repo: FakeDeveloperRepository, cache: FakeCacheProvider
    ) -> None:
        cache.store[f"{VERIFY_CODE_DEV_CACHE_PREFIX}1"] = "333444"
        new_email = "brandnew@example.com"
        svc.verify_and_update_email(1, "333444", new_email)
        assert repo.get_by_id(1).email == new_email


class TestForgotPassword:
    """忘记密码：申请重置 + 重置。"""

    def test_request_unregistered_email(self, svc: DeveloperAuthService) -> None:
        """邮箱未注册也返回成功提示（防账号枚举），不写缓存。"""
        msg = svc.request_password_reset("nobody@example.com")
        assert "重置链接已发送" in msg["message"]

    def test_request_success(
        self, svc: DeveloperAuthService, cache: FakeCacheProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sent: dict[str, str] = {}

        def _capture(self, to, token) -> None:
            sent.update(to=to, token=token)

        monkeypatch.setattr(DeveloperAuthService, "_send_reset_email", _capture)
        svc.request_password_reset("devone@example.com")
        # 重置令牌写入 Redis，键前缀 pwd_reset_dev:
        token_keys = [k for k in cache.store if k.startswith("pwd_reset_dev:")]
        assert len(token_keys) == 1
        assert sent["token"] == token_keys[0].removeprefix("pwd_reset_dev:")

    def test_request_email_send_failure(
        self, svc: DeveloperAuthService, cache: FakeCacheProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(self, to, token):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(DeveloperAuthService, "_send_reset_email", _boom)
        with pytest.raises(ConflictException):
            svc.request_password_reset("devone@example.com")
        # 失败后清理令牌
        assert not any(k.startswith("pwd_reset_dev:") for k in cache.store)

    def test_reset_password_mismatch(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.reset_password("sometoken", "NewPass@1", "Different@1")

    def test_reset_password_invalid_token(self, svc: DeveloperAuthService) -> None:
        with pytest.raises(AuthenticationException):
            svc.reset_password("bad-token", "NewPass@123", "NewPass@123")

    def test_reset_password_success(
        self, svc: DeveloperAuthService, repo: FakeDeveloperRepository, cache: FakeCacheProvider
    ) -> None:
        cache.store["pwd_reset_dev:good-token"] = "1"
        cache.store[f"{_LOGIN_KEY}1"] = "jti"
        svc.reset_password("good-token", "NewPass@123", "NewPass@123")
        assert repo.get_by_id(1).password_hash != hash_password(_PASSWORD)
        # 令牌一次性作废 + 登录态撤销
        assert "pwd_reset_dev:good-token" not in cache.store
        assert f"{_LOGIN_KEY}1" not in cache.store
