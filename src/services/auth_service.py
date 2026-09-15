#!/usr/bin/env python3
"""
认证业务逻辑实现

提供登录、令牌刷新、当前用户解析、退出登录能力。
登录态依赖 Redis 维护（login:{user_id} 记录当前有效的访问令牌 jti），
令牌本身使用 JWT（access/refresh）。登录成功/失败写入 login_logs 表。

Classes:
    AuthService: 认证业务逻辑实现
"""

import json
from datetime import UTC, datetime
from typing import Any

import jwt

from src.constants.enums import UserStatus
from src.core.config import settings
from src.core.exceptions import AuthenticationException, BusinessException, DatabaseException
from src.core.logger import logger
from src.core.security import verify_password
from src.core.tokens import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.infras.email import EmailProvider
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.user_entity import RoleEntity, UserEntity
from src.services.notification_service import NotificationService
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)

# Redis 登录态键前缀：login:{user_id} -> 当前生效的 access token jti
_LOGIN_KEY_PREFIX = "login:"
# 登录态默认过期时间（秒），与 access token 有效期对齐
_LOGIN_STATE_TTL = 60 * 60 * 24 * 7


class AuthService:
    """认证业务逻辑实现。"""

    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._user_repository: UserRepository = user_repository
        self._role_repository = role_repository or RoleRepository(
            session=user_repository.session
        )
        self._notification_service = notification_service or NotificationService(
            email_provider=EmailProvider()
        )

    def login(
        self,
        account: str,
        password: str,
        ip_address: str | None = None,
        client_type: str = "console",
    ) -> TokenResponse:
        """用户登录。

        校验用户名/邮箱 + 密码，成功后签发 access/refresh 令牌并写入 Redis 登录态。
        无论成功失败均记录 login_logs。
        """
        from src.infras.cache import get_cached_cache_provider

        user = self._find_account(account)

        success = False
        if user is not None and user.status != UserStatus.LOCKED.value:
            success = verify_password(password, user.password_hash or "")

        self._write_login_log(
            user_id=user.id if user else None,
            login_type="password",
            status="success" if success else "failed",
            ip_address=ip_address,
        )

        if not success or user is None:
            raise AuthenticationException(message="用户名/邮箱或密码错误")

        access_token = create_access_token(
            user.id, extra_claims={"username": user.username}
        )
        refresh_token = create_refresh_token(
            user.id, extra_claims={"username": user.username}
        )
        access_jti = decode_token(access_token).get("jti")

        # 维护 Redis 登录态：记录当前生效的 access token jti
        try:
            provider = get_cached_cache_provider()
            provider.set(
                f"{_LOGIN_KEY_PREFIX}{user.id}",
                access_jti or "",
                ttl=_LOGIN_STATE_TTL,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis 登录态写入失败（登录仍成功）: {e}")

        # 更新最后登录信息（直接操作 session，避免依赖 UserService）
        try:
            user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
            user.last_login_ip = ip_address
            self._user_repository.session.flush()
            self._user_repository.session.commit()
        except Exception as e:  # noqa: BLE001
            self._user_repository.session.rollback()
            logger.warning(f"更新最后登录信息失败: {e}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=60 * 60 * 24 * 7,
        )

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
        if user.status == UserStatus.LOCKED.value:
            raise AuthenticationException(message="用户已被锁定")

        access_token = create_access_token(
            user.id, extra_claims={"username": user.username}
        )
        new_refresh_token = create_refresh_token(
            user.id, extra_claims={"username": user.username}
        )
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
            expires_in=60 * 60 * 24 * 7,
        )

    def get_current_user(self, authorization: str | None) -> CurrentUserResponse:
        """解析 Bearer 令牌，返回当前登录用户（校验 Redis 登录态）。

        兼容两种 Authorization 头格式：
            - "Bearer <token>"（标准格式，大小写不敏感）
            - "<token>"（未带 Bearer 前缀，自动视为令牌）
        """
        from src.infras.cache import get_cached_cache_provider

        if not authorization or not authorization.strip():
            raise AuthenticationException(message="缺少或格式错误的 Authorization 头")

        auth_value = authorization.strip()
        if auth_value.lower().startswith("bearer "):
            token = auth_value[len("bearer ") :].strip()
        else:
            token = auth_value

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

        # 校验 Redis 登录态：令牌 jti 必须仍为当前生效令牌
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

        role_code: str | None = None
        if user.role_id is not None:
            role = self._role_repository.get_by_id(user.role_id)
            if role is not None:
                role_code = role.role_code

        return CurrentUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            age=user.age,
            role_id=user.role_id,
            role_code=role_code,
            status=user.status or UserStatus.ACTIVE.value,
            avatar_url=user.avatar_url,
            last_login_at=user.last_login_at,
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

    def _write_login_log(
        self,
        user_id: int | None,
        login_type: str,
        status: str,
        ip_address: str | None,
    ) -> None:
        """写入登录日志（login_logs 表）。"""
        try:
            log = LoginLogEntity(
                user_id=user_id,
                login_type=login_type,
                status=status,
                ip_address=ip_address,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            self._user_repository.session.add(log)
            self._user_repository.session.commit()
        except Exception as e:  # noqa: BLE001
            self._user_repository.session.rollback()
            logger.warning(f"写入登录日志失败: {e}")

    # ----------------------------------------------------------
    # 密码重置相关方法
    # ----------------------------------------------------------

    def _generate_reset_token(self, user_id: int, email: str) -> str:
        """生成密码重置令牌。

        使用 JWT 签发，包含用户 ID 和邮箱，有效期从配置读取。

        Args:
            user_id: 用户 ID
            email: 用户邮箱

        Returns:
            str: JWT 格式的重置令牌
        """
        from datetime import timedelta

        now = datetime.now(UTC)
        expire_minutes = settings.password_reset.token_expire_minutes
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "password_reset",
            "iat": now,
            "exp": now + timedelta(minutes=expire_minutes),
            "jti": f"reset-{user_id}-{now.timestamp():.0f}",
        }
        return jwt.encode(
            payload,
            settings.auth.secret_key,
            algorithm=settings.auth.algorithm,
        )

    def _verify_reset_token(self, token: str) -> dict[str, Any]:
        """验证密码重置令牌。

        Args:
            token: JWT 格式的重置令牌

        Returns:
            dict: 令牌载荷

        Raises:
            AuthenticationException: 令牌无效或已过期
        """
        try:
            payload = jwt.decode(
                token,
                settings.auth.secret_key,
                algorithms=[settings.auth.algorithm],
            )
            if payload.get("type") != "password_reset":
                raise AuthenticationException(message="无效的重置令牌类型")
            return payload
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationException(message="重置令牌已过期") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationException(message="无效的重置令牌") from e

    def _check_rate_limit(self, email: str) -> None:
        """检查密码重置请求频率限制。

        每个邮箱每小时最多请求 max_attempts_per_hour 次。

        Args:
            email: 用户邮箱

        Raises:
            BusinessException: 超过频率限制
        """
        from src.infras.cache import get_cached_cache_provider

        try:
            provider = get_cached_cache_provider()
            key = f"password_reset:attempts:{email}"
            attempts = provider.get(key)

            if attempts and int(attempts) >= settings.password_reset.max_attempts_per_hour:
                raise BusinessException(
                    message="密码重置请求过于频繁，请稍后再试",
                    code=429,
                )

            # 增加计数器，有效期 1 小时
            provider.atomic_incr(key, ttl=3600)
        except BusinessException:
            raise
        except Exception as e:
            logger.warning(f"Redis 频率限制检查失败（放行）: {e}")

    def request_password_reset(self, email: str) -> bool:
        """请求密码重置。

        流程：
        1. 验证邮箱是否存在
        2. 检查频率限制
        3. 生成重置令牌
        4. 发送重置邮件

        Args:
            email: 用户邮箱

        Returns:
            bool: 邮件发送成功返回 True

        Raises:
            NotFoundException: 邮箱不存在
            BusinessException: 超过频率限制
        """
        from src.core.exceptions import NotFoundException
        from src.infras.cache import get_cached_cache_provider

        # 查找用户
        user = self._user_repository.get_by_email(email)
        if user is None:
            raise NotFoundException(message="该邮箱未注册")

        if user.status == UserStatus.LOCKED.value:
            raise BusinessException(message="账户已被锁定，请联系管理员")

        # 检查频率限制
        self._check_rate_limit(email)

        # 生成令牌
        token = self._generate_reset_token(user.id, user.email)

        # 存储令牌到缓存（用于验证和撤销）
        try:
            provider = get_cached_cache_provider()
            key = f"password_reset:token:{user.id}"
            provider.set(
                key,
                token,
                ttl=settings.password_reset.token_expire_minutes * 60,
            )
        except Exception as e:
            logger.warning(f"Redis 令牌存储失败（继续发送邮件）: {e}")

        # 发送邮件
        return self._notification_service.send_password_reset_email(
            to_address=user.email,
            username=user.username,
            reset_token=token,
        )

    def verify_reset_token(self, token: str) -> dict[str, Any]:
        """验证密码重置令牌。

        Args:
            token: JWT 格式的重置令牌

        Returns:
            dict: 包含 valid、email（脱敏）、expires_at

        Raises:
            AuthenticationException: 令牌无效或已过期
        """
        from src.infras.cache import get_cached_cache_provider

        payload = self._verify_reset_token(token)

        user_id = int(payload.get("sub", 0))

        # 检查令牌是否已被撤销
        try:
            provider = get_cached_cache_provider()
            stored_token = provider.get(f"password_reset:token:{user_id}")
            if stored_token and stored_token != token:
                raise AuthenticationException(message="重置令牌已失效")
        except AuthenticationException:
            raise
        except Exception as e:
            logger.warning(f"Redis 令牌验证失败（放行）: {e}")

        # 脱敏邮箱
        email = payload.get("email", "")
        masked_email = self._mask_email(email)

        return {
            "valid": True,
            "email": masked_email,
            "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=UTC),
        }

    def reset_password(self, token: str, new_password: str) -> bool:
        """重置密码。

        流程：
        1. 验证令牌
        2. 更新密码
        3. 撤销令牌
        4. 清除登录态

        Args:
            token: JWT 格式的重置令牌
            new_password: 新密码

        Returns:
            bool: 重置成功返回 True

        Raises:
            AuthenticationException: 令牌无效或已过期
            DatabaseException: 数据库更新失败
        """
        from src.core.security import hash_password
        from src.infras.cache import get_cached_cache_provider

        # 验证令牌
        payload = self._verify_reset_token(token)
        user_id = int(payload.get("sub", 0))

        # 查找用户
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationException(message="用户不存在")

        # 更新密码
        try:
            user.password_hash = hash_password(new_password)
            self._user_repository.session.flush()
            self._user_repository.session.commit()
        except Exception as e:
            self._user_repository.session.rollback()
            logger.error(f"密码更新失败: {e}")
            raise DatabaseException(message="密码更新失败") from e

        # 撤销令牌
        try:
            provider = get_cached_cache_provider()
            provider.delete(f"password_reset:token:{user_id}")
        except Exception as e:
            logger.warning(f"Redis 令牌撤销失败: {e}")

        # 清除登录态（强制重新登录）
        self.logout(user_id)

        logger.info(f"密码重置成功: user_id={user_id}")
        return True

    @staticmethod
    def _mask_email(email: str) -> str:
        """邮箱脱敏处理。

        例如：user@example.com -> u***r@example.com

        Args:
            email: 原始邮箱

        Returns:
            str: 脱敏后的邮箱
        """
        if not email or "@" not in email:
            return email

        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local[0] + "***"
        else:
            masked_local = local[0] + "***" + local[-1]

        return f"{masked_local}@{domain}"
