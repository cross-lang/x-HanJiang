#!/usr/bin/env python3
"""
认证业务逻辑实现
提供登录、令牌刷新、当前用户解析、退出登录能力。
登录态依赖 Redis 维护（login:{user_id} 记录当前有效的访问令牌 jti），
令牌本身使用 JWT（access/refresh）。登录成功/失败写入 login_logs 表。

Classes:
    AuthService: 认证业务逻辑实现
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.constants.constants import TOKEN_TTL_SECONDS
from src.constants.enums import (
    LoginStatus,
    LoginType,
    NotificationEvent,
    NotificationSource,
    SystemRoleCode,
    UserStatus,
)
from src.core.exceptions import AuthenticationException
from src.core.logger import logger
from src.core.tokens import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.user_entity import UserEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.login_log_repository import LoginLogRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
from src.schemas.admin.auth import (
    CurrentUser,
    TokenResponse,
)
from src.utils.security import verify_password

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher

# Redis 登录态键前缀：login:{user_id} -> 当前生效的 access token jti
_LOGIN_KEY_PREFIX = "login:"

# 登录态默认过期时间（秒），与 access token 有效期对齐
_LOGIN_STATE_TTL = TOKEN_TTL_SECONDS


class AuthService:
    """认证业务逻辑实现。"""

    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository | None = None,
        login_log_repository: LoginLogRepository | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self._user_repository: UserRepository = user_repository
        self._role_repository = role_repository or RoleRepository(session=user_repository.session)
        self._login_log_repository = login_log_repository or LoginLogRepository(session=user_repository.session)
        self._dispatcher = dispatcher

    def login(
        self,
        account: str,
        password: str,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """用户登录。
        校验用户名/邮箱 + 密码，成功后签发 access/refresh 令牌并写入 Redis 登录态。
        无论成功失败均记录 login_logs。
        """
        user = self._find_account(account)
        success = False
        if user is not None and user.status == UserStatus.ENABLED.value:
            success = verify_password(password, user.password_hash or "")
        self._write_login_log(
            user_id=user.id if user else None,
            login_type=LoginType.PASSWORD.mark,
            status=LoginStatus.SUCCESS.mark if success else LoginStatus.FAILED.mark,
            ip_address=ip_address,
        )
        if not success or user is None:
            # ── 连续登录失败告警 ──
            if user is not None:
                self._check_login_failures(user, ip_address)
            raise AuthenticationException(message="用户名/邮箱或密码错误")
        # 新设备登录检测并通知（失败不阻断登录主流程）
        self._notify_new_device_login(user.id, ip_address or "")
        return self._issue_tokens(user, ip_address=ip_address)

    def _notify_new_device_login(self, user_id: int, ip: str) -> None:
        """检测新设备登录并发送通知（失败仅记录日志，不影响登录）。"""
        if self._dispatcher is None:
            return
        try:
            if self.detect_new_device_login(user_id, ip):
                self._dispatcher.dispatch_for_user(
                    user_id=user_id,
                    event_type=NotificationEvent.LOGIN_NEW_DEVICE,
                    variables={"ip": ip, "time": ""},
                    source=NotificationSource.MANUAL.value,
                )
        except Exception:  # noqa: BLE001
            logger.warning("新设备登录通知发送失败 user_id=%s", user_id)

    def detect_new_device_login(self, user_id: int, current_ip: str) -> bool:
        """判断本次登录是否来自新设备。
        与上一次成功登录（排除本次记录）的 IP 对比，不一致视为新设备。

        Args:
            user_id: 用户 ID
            current_ip: 本次登录 IP

        Returns:
            bool: 是否为新设备登录
        """
        last = self._login_log_repository.get_previous_success(user_id=user_id, skip=1)
        return last is not None and last.ip_address != current_ip

    def refresh(self, refresh_token: str) -> TokenResponse:
        """使用刷新令牌换取新的令牌对。"""
        from src.infras.cache import get_cached_cache_provider

        try:
            payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        except Exception as e:  # noqa: BLE001
            raise AuthenticationException(message=f"刷新令牌无效: {e}") from e
        user_id = int(payload.get("sub", 0))
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationException(message="用户不存在")
        if user.status == UserStatus.DISABLED.value:
            raise AuthenticationException(message="用户已被禁用")
        access_token = create_access_token(user.id, extra_claims={"username": user.username})
        new_refresh_token = create_refresh_token(user.id, extra_claims={"username": user.username})
        access_jti = decode_token(access_token).get("jti")
        try:
            provider = get_cached_cache_provider()
            provider.set(
                f"{_LOGIN_KEY_PREFIX}{user.id}",
                access_jti or "",
                ttl=_LOGIN_STATE_TTL,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis 登录态写入失败（刷新仍成功）: {e}")
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=TOKEN_TTL_SECONDS,
        )

    def get_current_user(self, authorization: str | None) -> CurrentUser:
        """解析 Bearer 令牌，返回当前登录用户（校验 Redis 登录态）。"""
        from src.infras.cache import get_cached_cache_provider

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
        user_id = int(payload.get("sub", 0))
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationException(message="用户不存在")
        # 校验 Redis 登录态
        try:
            provider = get_cached_cache_provider()
            stored_jti = provider.get(f"{_LOGIN_KEY_PREFIX}{user.id}")
            if stored_jti is None:
                raise AuthenticationException(message="登录态已失效，请重新登录")
            if stored_jti and stored_jti != payload.get("jti"):
                raise AuthenticationException(message="令牌已失效，请重新登录")
        except AuthenticationException:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis 登录态校验失败（放行）: {e}")
        # 从 user_roles 查用户角色（经仓库）
        roles = self._role_repository.get_by_user_id(user.id)
        role_codes = [r.role_code for r in roles]
        role_code = role_codes[0] if role_codes else None
        role_ids = [r.id for r in roles]
        # 查用户所有权限码（经仓库）
        permissions: list[str] = []
        if role_ids:
            permissions = self._user_repository.get_perm_codes_by_role_ids(role_ids)
        # 超管自动拥有所有权限标记
        if SystemRoleCode.SUPERADMIN.mark in role_codes:
            permissions = ["*"]
        return CurrentUser(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            role_code=role_code,
            status=user.status or UserStatus.ENABLED.value,
            avatar_url=user.avatar_url,
            phone=getattr(user, "phone", None),
            birthday=user.birthday.strftime("%Y-%m-%d") if user.birthday else None,
            gender=getattr(user, "gender", None),
            last_login_at=user.last_login_at,
            permissions=permissions,
        )

    def logout(self, user_id: int) -> None:
        """退出登录：清除 Redis 登录态。"""
        from src.infras.cache import get_cached_cache_provider

        try:
            provider = get_cached_cache_provider()
            provider.delete(f"{_LOGIN_KEY_PREFIX}{user_id}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis 登录态清除失败: {e}")

    def _find_account(self, account: str) -> UserEntity | None:
        """按用户名或邮箱查找用户。"""
        if "@" in account:
            return self._user_repository.get_by_email(account)
        return self._user_repository.get_by_username(account)

    def _check_login_failures(
        self,
        user: UserEntity,
        ip_address: str | None,
    ) -> None:
        """检查连续登录失败次数，超过阈值则发送告警通知。"""
        if self._dispatcher is None:
            return
        try:
            fail_count = self._login_log_repository.count_recent_failures(user_id=user.id, minutes=30)
            if fail_count >= 3:
                self._dispatcher.dispatch_for_user(
                    user_id=user.id,
                    event_type=NotificationEvent.USER_LOGIN_FAILED,
                    variables={
                        "username": user.username,
                        "fail_count": str(fail_count),
                        "attempt_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ip_address": ip_address or "未知",
                    },
                    source=NotificationSource.MANUAL.value,
                )
        except Exception as e:
            logger.warning(f"登录失败告警发送失败: user={user.id} error={e}")

    def _write_login_log(
        self,
        user_id: int | None,
        login_type: str,
        status: str,
        ip_address: str | None,
    ) -> None:
        """写入登录日志（login_logs 表，经仓库）。"""
        try:
            log = LoginLogEntity(
                user_id=user_id,
                login_type=login_type,
                status=status,
                ip_address=ip_address,
                created_at=datetime.now(),
            )
            self._login_log_repository.create(log)
            self._login_log_repository.commit()
        except Exception as e:  # noqa: BLE001
            self._login_log_repository.rollback()
            logger.warning(f"写入登录日志失败: {e}")

    def _issue_tokens(self, user: UserEntity, ip_address: str | None = None) -> TokenResponse:
        """为用户签发令牌并维护 Redis 登录态。"""
        from src.infras.cache import get_cached_cache_provider

        access_token = create_access_token(user.id, extra_claims={"username": user.username})
        refresh_token = create_refresh_token(user.id, extra_claims={"username": user.username})
        access_jti = decode_token(access_token).get("jti")
        try:
            provider = get_cached_cache_provider()
            provider.set(
                f"{_LOGIN_KEY_PREFIX}{user.id}",
                access_jti or "",
                ttl=_LOGIN_STATE_TTL,
            )
        except Exception as e:
            logger.warning(f"Redis 登录态写入失败: {e}")
        # 更新最后登录信息（经仓库）
        try:
            self._user_repository.update_last_login(
                user_id=user.id,
                last_login_at=datetime.now(),
                ip_address=ip_address,
            )
            self._user_repository.commit()
        except Exception as e:
            self._user_repository.rollback()
            logger.warning(f"更新最后登录信息失败: {e}")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=TOKEN_TTL_SECONDS,
        )
