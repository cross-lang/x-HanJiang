#!/usr/bin/env python3
"""开放平台开发者认证业务逻辑（有状态会话，对齐管理系统 AuthService）。

会话模型（混合会话：JWT + Redis 登录态）：
    - 登录成功签发 access/refresh 令牌，并将 access 令牌的 jti 写入 Redis
      `login_dev:{developer_id}`（TTL 与 access 令牌有效期对齐）；
    - 每个请求解析令牌时校验 Redis 中记录的 jti 与当前令牌一致，不一致即视为
      已失效（登出、刷新令牌、修改密码都会轮换/清除 jti，实现服务端可撤销）；
    - 与管理系统会话键 `login:{user_id}` 完全隔离（两者 ID 空间均从 1 起，避免冲突）。

Classes:
    DeveloperAuthService: 开发者认证业务逻辑实现
"""

from __future__ import annotations

from datetime import datetime

from src.constants.constants import TOKEN_TTL_SECONDS
from src.constants.enums import DeveloperStatus
from src.core.exceptions import AuthenticationException, ConflictException
from src.core.logger import logger
from src.core.tokens import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.infras.cache import CacheProvider
from src.models.entities.developer_entity import DeveloperEntity
from src.repositories.developer_repository import DeveloperRepository
from src.schemas.open_portal.auth import (
    CurrentDeveloper,
    DeveloperProfileResponse,
    DeveloperTokenResponse,
)
from src.utils.security import hash_password, verify_password

# Redis 登录态键前缀：login_dev:{developer_id} -> 当前生效的 access token jti
# （与管理端 login: 前缀隔离，防止开发者 ID 与用户 ID 空间互相覆盖）
_LOGIN_KEY_PREFIX = "login_dev:"

# 登录态默认过期时间（秒），与 access token 有效期对齐
_LOGIN_STATE_TTL = TOKEN_TTL_SECONDS


class DeveloperAuthService:
    """开发者认证业务逻辑实现。"""

    def __init__(self, repository: DeveloperRepository) -> None:
        self._repository = repository

    # ── 注册 ────────────────────────────────────────────

    def register(
        self,
        *,
        username: str,
        email: str,
        password: str,
        confirm_password: str,
        name: str | None = None,
        certification_type: str | None = None,
    ) -> DeveloperProfileResponse:
        """注册开发者账号。

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            confirm_password: 确认密码
            name: 昵称（可选，为空时回退为用户名）
            certification_type: 认证主体类型（预留）

        Returns:
            DeveloperProfileResponse: 注册成功的开发者资料

        Raises:
            AuthenticationException: 两次密码不一致
            ConflictException: 用户名或邮箱已存在
        """
        if password != confirm_password:
            raise AuthenticationException(message="两次输入的密码不一致")
        if self._repository.get_by_username(username) is not None:
            raise ConflictException(message="用户名已存在")
        if self._repository.get_by_email(email) is not None:
            raise ConflictException(message="邮箱已存在")
        entity = DeveloperEntity(
            username=username,
            email=email,
            password_hash=hash_password(password),
            name=name or username,
            certification_type=certification_type,
            status=DeveloperStatus.ENABLED.value,
        )
        created = self._repository.create(entity)
        self._repository.commit()
        return self._to_profile(created)

    # ── 登录 ────────────────────────────────────────────

    def login(self, account: str, password: str) -> DeveloperTokenResponse:
        """开发者登录（账号=用户名或邮箱），成功后签发令牌对并写入 Redis 登录态。"""
        dev = self._find_account(account)
        if dev is None or not verify_password(password, dev.password_hash or ""):
            raise AuthenticationException(message="用户名/邮箱或密码错误")
        if dev.status != DeveloperStatus.ENABLED.value:
            raise AuthenticationException(message="账号已被禁用")
        return self._issue_tokens(dev)

    # ── 刷新令牌 ────────────────────────────────────────

    def refresh(self, refresh_token: str) -> DeveloperTokenResponse:
        """使用刷新令牌换取新的令牌对（旧 access 令牌随之失效）。"""
        try:
            payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        except Exception as e:  # noqa: BLE001
            raise AuthenticationException(message=f"刷新令牌无效: {e}") from e
        dev_id = int(payload.get("sub", 0))
        dev = self._repository.get_by_id(dev_id)
        if dev is None:
            raise AuthenticationException(message="开发者不存在")
        if dev.status != DeveloperStatus.ENABLED.value:
            raise AuthenticationException(message="账号已被禁用")
        return self._issue_tokens(dev)

    # ── 当前开发者解析 ──────────────────────────────────

    def get_current_developer(self, authorization: str | None) -> CurrentDeveloper:
        """解析 Bearer 令牌，返回当前开发者（校验 Redis 登录态，登出/改密后即失效）。"""
        if not authorization or not authorization.strip():
            raise AuthenticationException(message="缺少或格式错误的 Authorization 头")
        auth_value = authorization.strip()
        token = auth_value[len("bearer ") :].strip() if auth_value.lower().startswith("bearer ") else auth_value
        if not token:
            raise AuthenticationException(message="缺少或格式错误的 Authorization 头")
        try:
            payload = decode_token(token, expected_type="access")
        except Exception as e:  # noqa: BLE001
            raise AuthenticationException(message=f"令牌无效: {e}") from e
        dev_id = int(payload.get("sub", 0))
        dev = self._repository.get_by_id(dev_id)
        if dev is None:
            raise AuthenticationException(message="开发者不存在")
        if dev.status != DeveloperStatus.ENABLED.value:
            raise AuthenticationException(message="账号已被禁用")
        # 校验 Redis 登录态：会话不存在或 jti 不匹配 → 视为已撤销
        try:
            provider = self._cache_provider()
            stored_jti = provider.get(f"{_LOGIN_KEY_PREFIX}{dev.id}")
            if stored_jti is None:
                raise AuthenticationException(message="登录态已失效，请重新登录")
            if stored_jti and stored_jti != payload.get("jti"):
                raise AuthenticationException(message="令牌已失效，请重新登录")
        except AuthenticationException:
            raise
        except Exception as e:  # noqa: BLE001
            # Redis 不可用时不阻断主流程（与管理系统 AuthService 行为对齐），仅记录告警
            logger.warning(f"Redis 登录态校验失败（放行）: {e}")
        return CurrentDeveloper(
            id=dev.id,
            username=dev.username,
            email=dev.email,
            name=dev.name,
            phone=dev.phone,
            status=dev.status,
        )

    # ── 退出登录 ────────────────────────────────────────

    def logout(self, developer_id: int) -> None:
        """退出登录：清除 Redis 登录态，当前所有已签发 access 令牌立即失效。"""
        try:
            provider = self._cache_provider()
            provider.delete(f"{_LOGIN_KEY_PREFIX}{developer_id}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis 登录态清除失败: {e}")

    # ── 修改密码 ────────────────────────────────────────

    def change_password(self, developer_id: int, old_password: str, new_password: str) -> None:
        """修改密码：校验原密码后更新哈希，并清除 Redis 登录态（强制重新登录）。"""
        dev = self._repository.get_by_id(developer_id)
        if dev is None:
            raise AuthenticationException(message="开发者不存在")
        if not verify_password(old_password, dev.password_hash or ""):
            raise AuthenticationException(message="原密码不正确")
        dev.password_hash = hash_password(new_password)
        self._repository.commit()
        # 改密后撤销全部已签发令牌（开发者域无验证码二次认证，改密即失效更安全）
        self.logout(developer_id)

    # ── 内部工具 ────────────────────────────────────────

    def _issue_tokens(self, dev: DeveloperEntity) -> DeveloperTokenResponse:
        """签发令牌对并维护 Redis 登录态。"""
        from src.infras.cache import get_cached_cache_provider

        access_token = create_access_token(dev.id, extra_claims={"username": dev.username, "scope": "developer"})
        refresh_token = create_refresh_token(dev.id, extra_claims={"username": dev.username, "scope": "developer"})
        access_jti = decode_token(access_token).get("jti")
        try:
            provider = get_cached_cache_provider()
            provider.set(
                f"{_LOGIN_KEY_PREFIX}{dev.id}",
                access_jti or "",
                ttl=_LOGIN_STATE_TTL,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis 登录态写入失败: {e}")
        try:
            self._repository.update_last_login(dev.id, datetime.now())
            self._repository.commit()
        except Exception:  # noqa: BLE001
            self._repository.rollback()
        return DeveloperTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=TOKEN_TTL_SECONDS,
        )

    def _cache_provider(self) -> CacheProvider:
        """延迟获取 Redis 缓存提供者。"""
        from src.infras.cache import get_cached_cache_provider

        return get_cached_cache_provider()

    def _find_account(self, account: str) -> DeveloperEntity | None:
        """按用户名或邮箱查找开发者。"""
        if "@" in account:
            return self._repository.get_by_email(account)
        return self._repository.get_by_username(account)

    def _to_profile(self, e: DeveloperEntity) -> DeveloperProfileResponse:
        return DeveloperProfileResponse(
            id=e.id,
            username=e.username,
            email=e.email,
            name=e.name,
            phone=e.phone,
            certification_type=e.certification_type,
            certification_status=e.certification_status,
            company_name=e.company_name,
            created_at=e.created_at,
        )
