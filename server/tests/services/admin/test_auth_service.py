#!/usr/bin/env python3
"""管理端认证服务（AuthService）单元测试。

覆盖目标模块 src/services/admin/auth_service.py：
    - 登录三通道识别（用户名 / 邮箱 / 手机号，含手机号回退用户名）
    - 登录成功 / 用户不存在 / 密码错误 / 账号禁用分支
    - 连续失败告警（dispatcher 注入）
    - 新设备登录检测
    - 刷新令牌、当前用户解析（含 Redis 登录态校验各分支）、退出登录

外部依赖一律离线替身：bcrypt/PyJWT 真实可用，Redis 用内存 Fake，不触网、不连库。
"""

from types import SimpleNamespace

import pytest
from src.core.exceptions import AuthenticationException
from src.core.tokens import create_access_token, create_refresh_token, decode_token
from src.models.entities.user_entity import UserEntity
from src.services.admin.auth_service import AuthService
from src.utils.security import hash_password

# 测试统一口令（bcrypt 真实哈希，离线可校验）
_PASSWORD = "S3cret@123"
# 登录态缓存键前缀，与被测实现保持一致（避免硬编码业务语义外的魔数）
_LOGIN_KEY = "login:"


class FakeCacheProvider:
    """内存版缓存提供者替身（记录 get/set/delete）。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        # 指定哪些操作抛异常，用于覆盖"Redis 不可用放行/告警"分支
        self.raise_on: set[str] = set()

    def get(self, key: str):
        if "get" in self.raise_on:
            raise RuntimeError("redis down")
        return self.store.get(key)

    def set(self, key: str, value, ttl: int = 300) -> None:
        if "set" in self.raise_on:
            raise RuntimeError("redis down")
        self.store[key] = value

    def delete(self, key: str) -> None:
        if "delete" in self.raise_on:
            raise RuntimeError("redis down")
        self.store.pop(key, None)


class FakeUserRepository:
    """内存版用户仓库替身（接口与 UserRepository 对齐）。"""

    session = None

    def __init__(self) -> None:
        self._items: dict[int, UserEntity] = {}
        self.perm_codes: list[str] = []
        self.last_login_updates: list[dict] = []
        self.committed = 0
        self.rolled_back = 0

    def add(self, user: UserEntity) -> UserEntity:
        self._items[user.id] = user
        return user

    def get_by_id(self, id: int) -> UserEntity | None:
        return self._items.get(id)

    def get_by_username(self, username: str) -> UserEntity | None:
        return next((u for u in self._items.values() if u.username == username), None)

    def get_by_email(self, email: str) -> UserEntity | None:
        return next((u for u in self._items.values() if u.email == email), None)

    def get_by_phone(self, phone: str) -> UserEntity | None:
        return next((u for u in self._items.values() if u.phone == phone), None)

    def get_perm_codes_by_role_ids(self, role_ids: list[int]) -> list[str]:
        return list(self.perm_codes)

    def update_last_login(self, user_id: int, last_login_at, ip_address) -> None:
        existing = self._items.get(user_id)
        if existing is not None:
            existing.last_login_at = last_login_at
        self.last_login_updates.append({"user_id": user_id, "ip": ip_address})

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class FakeRoleRepository:
    """内存版角色仓库替身：get_by_user_id 返回带 id/role_code 的对象列表。"""

    def __init__(self) -> None:
        self.roles_by_user: dict[int, list[SimpleNamespace]] = {}

    def get_by_user_id(self, user_id: int) -> list[SimpleNamespace]:
        return list(self.roles_by_user.get(user_id, []))


class FakeLoginLogRepository:
    """内存版登录日志仓库替身：记录写入并提供可配置的统计/上一条查询。"""

    def __init__(self) -> None:
        self.created: list = []
        self.previous_success = None
        self.recent_failures = 0
        self.committed = 0
        self.rolled_back = 0

    def create(self, log) -> None:
        self.created.append(log)

    def get_previous_success(self, user_id: int, skip: int = 1):
        return self.previous_success

    def count_recent_failures(self, user_id: int, minutes: int = 30) -> int:
        return self.recent_failures

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class FakeDispatcher:
    """记录通知派发调用的替身。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def dispatch_for_user(self, **kwargs) -> None:
        self.calls.append(kwargs)


def _make_user(
    user_id: int = 1,
    username: str = "alice",
    email: str = "alice@example.com",
    phone: str = "13800000001",
    status: str = "enabled",
) -> UserEntity:
    """构造一个启用态用户，密码哈希为统一口令。"""
    return UserEntity(
        id=user_id,
        username=username,
        email=email,
        name="Alice",
        password_hash=hash_password(_PASSWORD),
        phone=phone,
        status=status,
    )


def _make_service(
    user_repo: FakeUserRepository,
    role_repo: FakeRoleRepository | None = None,
    login_log_repo: FakeLoginLogRepository | None = None,
    dispatcher: FakeDispatcher | None = None,
) -> AuthService:
    """组装 AuthService，注入全部内存替身。"""
    return AuthService(
        user_repository=user_repo,
        role_repository=role_repo or FakeRoleRepository(),
        login_log_repository=login_log_repo or FakeLoginLogRepository(),
        dispatcher=dispatcher,
    )


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch) -> FakeCacheProvider:
    """把 Redis 缓存提供者替换为内存 Fake（patch 目标模块内的工厂引用）。"""
    fake = FakeCacheProvider()
    monkeypatch.setattr("src.infras.cache.get_cached_cache_provider", lambda: fake)
    return fake


class TestLogin:
    """登录主流程与三通道识别。"""

    def test_login_success_by_username(self, cache: FakeCacheProvider) -> None:
        """用户名 + 正确密码登录成功，签发令牌并写入登录态。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        login_log_repo = FakeLoginLogRepository()
        svc = _make_service(user_repo, login_log_repo=login_log_repo)

        resp = svc.login("alice", _PASSWORD, ip_address="1.2.3.4")
        assert resp.token_type == "Bearer"
        assert resp.access_token and resp.refresh_token
        # 成功登录写了一条 success 日志
        assert login_log_repo.created[-1].status == "success"
        # Redis 登录态写入 access 令牌 jti
        assert cache.store.get(f"{_LOGIN_KEY}1")
        # 更新了最后登录信息
        assert user_repo.last_login_updates[-1]["ip"] == "1.2.3.4"

    def test_login_by_email_channel(self, cache: FakeCacheProvider) -> None:
        """含 @ 的账号走邮箱通道识别。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        svc = _make_service(user_repo)

        resp = svc.login("alice@example.com", _PASSWORD)
        assert resp.access_token

    def test_login_by_phone_channel(self, cache: FakeCacheProvider) -> None:
        """11 位纯数字账号走手机号通道命中。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        svc = _make_service(user_repo)

        resp = svc.login("13800000001", _PASSWORD)
        assert resp.access_token

    def test_login_phone_falls_back_to_username(self, cache: FakeCacheProvider) -> None:
        """11 位手机号未命中时回退按用户名查（兼容存量账号）。"""
        user_repo = FakeUserRepository()
        # 用户没有绑定该手机号，但用户名恰好是 11 位数字
        user_repo.add(_make_user(username="13900000002", phone=""))
        svc = _make_service(user_repo)

        resp = svc.login("13900000002", _PASSWORD)
        assert resp.access_token

    def test_login_user_not_found(self, cache: FakeCacheProvider) -> None:
        """账号不存在 → 认证异常，并记录失败日志。"""
        user_repo = FakeUserRepository()
        login_log_repo = FakeLoginLogRepository()
        svc = _make_service(user_repo, login_log_repo=login_log_repo)

        with pytest.raises(AuthenticationException):
            svc.login("ghost", _PASSWORD)
        assert login_log_repo.created[-1].status == "failed"

    def test_login_wrong_password(self, cache: FakeCacheProvider) -> None:
        """密码错误 → 认证异常。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        svc = _make_service(user_repo)

        with pytest.raises(AuthenticationException):
            svc.login("alice", "wrong-password")

    def test_login_disabled_user(self, cache: FakeCacheProvider) -> None:
        """账号被禁用 → 认证异常。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user(status="disabled"))
        svc = _make_service(user_repo)

        with pytest.raises(AuthenticationException):
            svc.login("alice", _PASSWORD)

    def test_login_failure_triggers_alert_when_threshold_exceeded(self, cache: FakeCacheProvider) -> None:
        """连续失败达阈值（>=3）时派发告警通知。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        login_log_repo = FakeLoginLogRepository()
        login_log_repo.recent_failures = 3
        dispatcher = FakeDispatcher()
        svc = _make_service(user_repo, login_log_repo=login_log_repo, dispatcher=dispatcher)

        with pytest.raises(AuthenticationException):
            svc.login("alice", "wrong-password")
        assert len(dispatcher.calls) == 1

    def test_login_failure_below_threshold_no_alert(self, cache: FakeCacheProvider) -> None:
        """失败次数未达阈值不告警。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        login_log_repo = FakeLoginLogRepository()
        login_log_repo.recent_failures = 1
        dispatcher = FakeDispatcher()
        svc = _make_service(user_repo, login_log_repo=login_log_repo, dispatcher=dispatcher)

        with pytest.raises(AuthenticationException):
            svc.login("alice", "wrong-password")
        assert dispatcher.calls == []


class TestNewDeviceDetect:
    """新设备登录检测分支。"""

    def test_detect_new_ip_true(self) -> None:
        """上一次成功登录 IP 与本次不同 → 新设备。"""
        user_repo = FakeUserRepository()
        login_log_repo = FakeLoginLogRepository()
        login_log_repo.previous_success = SimpleNamespace(ip_address="1.1.1.1")
        svc = _make_service(user_repo, login_log_repo=login_log_repo)

        assert svc.detect_new_device_login(1, "2.2.2.2") is True

    def test_detect_same_ip_false(self) -> None:
        """IP 相同 → 非新设备。"""
        user_repo = FakeUserRepository()
        login_log_repo = FakeLoginLogRepository()
        login_log_repo.previous_success = SimpleNamespace(ip_address="1.1.1.1")
        svc = _make_service(user_repo, login_log_repo=login_log_repo)

        assert svc.detect_new_device_login(1, "1.1.1.1") is False

    def test_detect_no_previous_false(self) -> None:
        """无上一次成功登录记录 → 非新设备。"""
        user_repo = FakeUserRepository()
        svc = _make_service(user_repo)
        assert svc.detect_new_device_login(1, "1.1.1.1") is False


class TestRefresh:
    """刷新令牌分支。"""

    def test_refresh_success(self, cache: FakeCacheProvider) -> None:
        """合法 refresh 令牌换取新令牌对。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        svc = _make_service(user_repo)
        old_refresh = create_refresh_token(1, extra_claims={"username": "alice"})

        resp = svc.refresh(old_refresh)
        assert resp.access_token and resp.refresh_token
        # 刷新后登录态轮换为新 access 的 jti
        assert cache.store.get(f"{_LOGIN_KEY}1")

    def test_refresh_invalid_token(self, cache: FakeCacheProvider) -> None:
        """伪造/损坏的 refresh 令牌 → 认证异常。"""
        user_repo = FakeUserRepository()
        svc = _make_service(user_repo)
        with pytest.raises(AuthenticationException):
            svc.refresh("not-a-jwt")

    def test_refresh_user_not_found(self, cache: FakeCacheProvider) -> None:
        """令牌合法但用户已不存在 → 认证异常。"""
        user_repo = FakeUserRepository()
        svc = _make_service(user_repo)
        token = create_refresh_token(999)
        with pytest.raises(AuthenticationException):
            svc.refresh(token)

    def test_refresh_disabled_user(self, cache: FakeCacheProvider) -> None:
        """用户被禁用后刷新 → 认证异常。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user(status="disabled"))
        svc = _make_service(user_repo)
        token = create_refresh_token(1)
        with pytest.raises(AuthenticationException):
            svc.refresh(token)


class TestGetCurrentUser:
    """当前用户解析（Bearer 令牌 + Redis 登录态校验）。"""

    def _seed_logged_in_user(self, user_repo: FakeUserRepository, cache: FakeCacheProvider) -> str:
        """登录成功后返回 access 令牌，并把 jti 写入缓存。"""
        svc = _make_service(user_repo)
        svc.login("alice", _PASSWORD)
        token = create_access_token(1, extra_claims={"username": "alice"})
        cache.store[f"{_LOGIN_KEY}1"] = decode_token(token).get("jti")
        return token

    def test_missing_authorization_header(self, cache: FakeCacheProvider) -> None:
        """缺少 Authorization 头 → 认证异常。"""
        svc = _make_service(FakeUserRepository())
        with pytest.raises(AuthenticationException):
            svc.get_current_user(None)
        with pytest.raises(AuthenticationException):
            svc.get_current_user("   ")

    def test_invalid_token(self, cache: FakeCacheProvider) -> None:
        """令牌损坏 → 认证异常。"""
        svc = _make_service(FakeUserRepository())
        with pytest.raises(AuthenticationException):
            svc.get_current_user("Bearer garbage")

    def test_user_not_found(self, cache: FakeCacheProvider) -> None:
        """令牌合法但用户不存在 → 认证异常。"""
        svc = _make_service(FakeUserRepository())
        token = create_access_token(999)
        with pytest.raises(AuthenticationException):
            svc.get_current_user(f"Bearer {token}")

    def test_login_state_missing(self, cache: FakeCacheProvider) -> None:
        """Redis 无登录态 → 认证异常。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        svc = _make_service(user_repo)
        token = create_access_token(1)
        # 不预置缓存登录态
        with pytest.raises(AuthenticationException):
            svc.get_current_user(f"Bearer {token}")

    def test_jti_mismatch(self, cache: FakeCacheProvider) -> None:
        """缓存 jti 与令牌 jti 不一致 → 认证异常。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        cache.store[f"{_LOGIN_KEY}1"] = "stale-jti"
        svc = _make_service(user_repo)
        token = create_access_token(1)
        with pytest.raises(AuthenticationException):
            svc.get_current_user(f"Bearer {token}")

    def test_success_with_roles_and_perms(self, cache: FakeCacheProvider) -> None:
        """解析成功：携带角色与权限码。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        user_repo.perm_codes = ["user:view"]
        role_repo = FakeRoleRepository()
        role_repo.roles_by_user[1] = [SimpleNamespace(id=10, role_code="admin")]
        svc = _make_service(user_repo, role_repo)
        token = self._seed_logged_in_user(user_repo, cache)

        current = svc.get_current_user(f"Bearer {token}")
        assert current.id == 1
        assert current.role_code == "admin"
        assert current.permissions == ["user:view"]

    def test_superadmin_gets_all_permissions(self, cache: FakeCacheProvider) -> None:
        """超管角色自动拥有全部权限标记 ['*']。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        role_repo = FakeRoleRepository()
        role_repo.roles_by_user[1] = [SimpleNamespace(id=10, role_code="superadmin")]
        svc = _make_service(user_repo, role_repo)
        token = self._seed_logged_in_user(user_repo, cache)

        current = svc.get_current_user(token)  # 不带 Bearer 前缀也应能解析
        assert current.permissions == ["*"]

    def test_redis_failure_still_passes_through(self, cache: FakeCacheProvider) -> None:
        """Redis 登录态校验异常时放行（不阻断），仍返回用户。"""
        user_repo = FakeUserRepository()
        user_repo.add(_make_user())
        svc = _make_service(user_repo)
        token = create_access_token(1)
        cache.raise_on.add("get")  # provider.get 抛异常
        current = svc.get_current_user(f"Bearer {token}")
        assert current.id == 1


class TestLogout:
    """退出登录分支。"""

    def test_logout_deletes_login_state(self, cache: FakeCacheProvider) -> None:
        """登出清除 Redis 登录态。"""
        cache.store[f"{_LOGIN_KEY}1"] = "some-jti"
        svc = _make_service(FakeUserRepository())
        svc.logout(1)
        assert f"{_LOGIN_KEY}1" not in cache.store

    def test_logout_swallows_redis_error(self, cache: FakeCacheProvider) -> None:
        """Redis 清除失败仅告警，不抛异常。"""
        cache.raise_on.add("delete")
        svc = _make_service(FakeUserRepository())
        svc.logout(1)  # 不应抛
