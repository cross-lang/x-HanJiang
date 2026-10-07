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

import contextlib
import random
import secrets
from datetime import datetime

from src.constants.constants import TOKEN_TTL_SECONDS
from src.constants.enums import DeveloperStatus
from src.core.config import settings
from src.core.exceptions import AuthenticationException, ConflictException, ValidationException
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
from src.schemas.open_portal.auth import CurrentDeveloper, DeveloperTokenResponse
from src.schemas.open_portal.developer import DeveloperProfileResponse
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
        name: str,
        certification_type: str,
    ) -> DeveloperProfileResponse:
        """注册开发者账号。

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            confirm_password: 确认密码
            name: 昵称（必填）
            certification_type: 认证主体类型（personal/enterprise，必填）

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
            name=name,
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

    def change_password(self, developer_id: int, old_password: str, new_password: str, code: str) -> None:
        """修改密码：校验原密码与邮箱验证码后更新哈希，并清除 Redis 登录态（强制重新登录）。

        Args:
            developer_id: 当前开发者 ID
            old_password: 原密码
            new_password: 新密码
            code: 邮箱验证码（二次认证）

        Raises:
            AuthenticationException: 开发者不存在或原密码不正确时抛出
            ValidationException: 验证码错误或已过期时抛出
        """
        dev = self._require_developer(developer_id)
        if not verify_password(old_password, dev.password_hash or ""):
            raise AuthenticationException(message="原密码不正确")
        if not self._check_email_code(developer_id, code):
            raise ValidationException(message="验证码错误或已过期")
        dev.password_hash = hash_password(new_password)
        self._repository.commit()
        # 改密后撤销全部已签发令牌（强制重新登录）
        self.logout(developer_id)

    # ── 安全设置：邮箱二次认证（修改手机号 / 邮箱）──────────

    def send_verify_code(self, developer_id: int) -> None:
        """向当前开发者邮箱发送 6 位验证码（5 分钟有效）。

        安全策略：
        - 验证码仅存 Redis（键 `verify_code_dev:{id}`，与管理端 `verify_code:{user_id}` 隔离）；
        - 邮件发送失败抛出业务异常，前端可感知失败而非静默成功。

        Args:
            developer_id: 当前开发者 ID

        Raises:
            ValidationException: 账号未绑定邮箱或验证码邮件发送失败时抛出
        """
        from src.constants.constants import (
            VERIFY_CODE_DEV_CACHE_PREFIX,
            VERIFY_CODE_MAX,
            VERIFY_CODE_MIN,
            VERIFY_CODE_TTL_SECONDS,
        )

        dev = self._require_developer(developer_id)
        if not dev.email:
            raise ValidationException(message="当前账号未绑定邮箱，无法发送验证码")
        code = f"{random.randint(VERIFY_CODE_MIN, VERIFY_CODE_MAX)}"
        try:
            provider = self._cache_provider()
            provider.set(
                f"{VERIFY_CODE_DEV_CACHE_PREFIX}{dev.id}",
                code,
                ttl=VERIFY_CODE_TTL_SECONDS,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"开发者验证码写入 Redis 失败: developer_id={dev.id} error={e}")
            raise ConflictException(message="验证码生成失败，请稍后重试") from e
        try:
            self._dispatch_verify_email(dev.email, code, dev.name or dev.username)
        except Exception as e:  # noqa: BLE001
            with contextlib.suppress(Exception):
                provider.delete(f"{VERIFY_CODE_DEV_CACHE_PREFIX}{dev.id}")
            logger.error(f"开发者验证码邮件发送失败: developer_id={dev.id} error={e}")
            raise ConflictException(message="验证码邮件发送失败，请稍后重试") from e

    def verify_and_update_phone(self, developer_id: int, code: str, phone: str) -> None:
        """通过验证码校验后修改开发者手机号。

        Args:
            developer_id: 当前开发者 ID
            code: 验证码（一次性）
            phone: 新手机号

        Raises:
            AuthenticationException: 开发者不存在时抛出
            ValidationException: 验证码错误或已过期时抛出
        """
        dev = self._require_developer(developer_id)
        if not self._check_email_code(developer_id, code):
            raise ValidationException(message="验证码错误或已过期")
        dev.phone = phone
        self._repository.commit()

    def verify_and_update_email(self, developer_id: int, code: str, email: str) -> None:
        """通过原验证码校验后修改开发者邮箱。

        Args:
            developer_id: 当前开发者 ID
            code: 原验证码（一次性）
            email: 新邮箱地址

        Raises:
            AuthenticationException: 开发者不存在时抛出
            ValidationException: 验证码错误/已过期，或新邮箱已被占用时抛出
        """
        dev = self._require_developer(developer_id)
        if not self._check_email_code(developer_id, code):
            raise ValidationException(message="原验证码错误或已过期")
        existing = self._repository.get_by_email(email)
        if existing is not None and existing.id != developer_id:
            raise ConflictException(message="该邮箱已被其他开发者绑定")
        dev.email = email
        self._repository.commit()

    def _require_developer(self, developer_id: int) -> DeveloperEntity:
        """按 ID 查询开发者，不存在时抛出认证异常。"""
        dev = self._repository.get_by_id(developer_id)
        if dev is None:
            raise AuthenticationException(message="开发者不存在")
        return dev

    def _check_email_code(self, developer_id: int, code: str) -> bool:
        """校验验证码（一次性，校验通过后立即删除）。

        Args:
            developer_id: 开发者 ID
            code: 待校验的验证码

        Returns:
            bool: 校验是否通过
        """
        from src.constants.constants import VERIFY_CODE_DEV_CACHE_PREFIX

        if not code:
            return False
        key = f"{VERIFY_CODE_DEV_CACHE_PREFIX}{developer_id}"
        saved = self._cache_provider().get(key)
        if saved != code:
            return False
        with contextlib.suppress(Exception):
            self._cache_provider().delete(key)
        return True

    def _dispatch_verify_email(self, to_email: str, code: str, username: str) -> None:
        """通过通知调度器向开发者邮箱发送验证码邮件（复用管理系统同款事件与模板）。"""
        from src.constants.constants import VERIFY_CODE_EVENT
        from src.infras.notification import get_registry
        from src.notification.dispatcher import NotificationDispatcher

        dispatcher = NotificationDispatcher(
            registry=get_registry(),
            session=self._repository.session,
        )
        dispatcher.dispatch(
            event_type=VERIFY_CODE_EVENT,
            recipients={"email": to_email},
            variables={"code": code, "username": username},
        )

    # ── 忘记密码（邮箱二次认证）─────────────────────────

    # 重置令牌键前缀：pwd_reset_dev:{token} -> developer_id
    _PWD_RESET_KEY_PREFIX = "pwd_reset_dev:"
    # 重置令牌有效期（秒）
    _PWD_RESET_TTL = 30 * 60

    def request_password_reset(self, email: str) -> dict[str, str]:
        """忘记密码：向注册邮箱发送含重置令牌的邮件。

        安全策略：
        - 邮箱不存在时同样返回成功提示，避免账号枚举；
        - 令牌为 32 字节随机串，仅存 Redis（TTL 30 分钟），不落库；
        - 邮件发送失败抛出业务异常（仅发生在账号存在且 SMTP 异常时）。
        """
        dev = self._repository.get_by_email(email)
        if dev is None:
            logger.info("forgot password for unregistered email=%s", email)
            return {
                "message": "如果该邮箱已注册，重置链接已发送至邮箱，请查收（30 分钟内有效）"
            }
        token = secrets.token_urlsafe(32)
        try:
            provider = self._cache_provider()
            provider.set(
                f"{self._PWD_RESET_KEY_PREFIX}{token}",
                str(dev.id),
                ttl=self._PWD_RESET_TTL,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"重置令牌写入 Redis 失败: {e}")
            raise ConflictException(message="重置令牌生成失败，请稍后重试") from e
        try:
            self._send_reset_email(dev.email, token)
        except Exception as e:  # noqa: BLE001
            # 清理令牌，避免无效令牌残留
            with contextlib.suppress(Exception):
                provider.delete(f"{self._PWD_RESET_KEY_PREFIX}{token}")
            logger.error(f"重置邮件发送失败: email={email} error={e}")
            raise ConflictException(message="重置邮件发送失败，请稍后重试或联系管理员") from e
        return {
            "message": "如果该邮箱已注册，重置链接已发送至邮箱，请查收（30 分钟内有效）"
        }

    def reset_password(self, token: str, new_password: str, confirm_password: str) -> None:
        """重置密码：校验邮件中的令牌后更新密码，撤销该开发者全部登录态并作废令牌。"""
        if new_password != confirm_password:
            raise AuthenticationException(message="两次输入的密码不一致")
        try:
            provider = self._cache_provider()
            dev_id_raw = provider.get(f"{self._PWD_RESET_KEY_PREFIX}{token}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"重置令牌校验失败: {e}")
            raise AuthenticationException(message="重置链接无效或已过期，请重新申请") from e
        if dev_id_raw is None:
            raise AuthenticationException(message="重置链接无效或已过期，请重新申请")
        dev = self._repository.get_by_id(int(dev_id_raw))
        if dev is None:
            raise AuthenticationException(message="开发者不存在，请联系管理员")
        dev.password_hash = hash_password(new_password)
        self._repository.commit()
        # 重置后：撤销全部登录态（强制重新登录）+ 作废令牌（一次性）
        self.logout(dev.id)
        try:
            provider.delete(f"{self._PWD_RESET_KEY_PREFIX}{token}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"重置令牌删除失败: {e}")
        logger.info("developer password reset via email: id=%s", dev.id)

    def _send_reset_email(self, to_email: str, token: str) -> None:
        """发送密码重置邮件（HTML 正文，含一次性重置链接）。"""
        from src.infras.email import get_cached_email_provider

        reset_url = f"{settings.open_portal_base_url}/reset-password?token={token}"
        subject = "汉江开放平台 - 密码重置"
        card_style = (
            "font-family:'Microsoft YaHei',Arial,sans-serif;max-width:600px;"
            "margin:0 auto;padding:24px;border:1px solid #e5e7eb;border-radius:8px;"
        )
        para_style = "font-size:14px;color:#333;line-height:1.7;"
        btn_style = (
            "display:inline-block;padding:10px 28px;background:#409eff;color:#fff;"
            "text-decoration:none;border-radius:6px;font-size:14px;"
        )
        html = f"""
        <div style="{card_style}">
          <div style="font-size:20px;font-weight:700;color:#1f3a5f;margin-bottom:16px;">
            汉江开放平台 - 密码重置
          </div>
          <p style="{para_style}">您好：</p>
          <p style="{para_style}">
            您正在重置汉江开放平台的登录密码。请点击下方链接完成重置，
            <b style="color:#e6a23c;">链接 30 分钟内有效，且仅可使用一次</b>：
          </p>
          <p style="text-align:center;margin:24px 0;">
            <a href="{reset_url}" style="{btn_style}">立即重置密码</a>
          </p>
          <p style="font-size:13px;color:#888;line-height:1.6;">
            如果按钮无法点击，请复制以下链接到浏览器地址栏打开：<br/>
            <span style="color:#409eff;word-break:break-all;">{reset_url}</span>
          </p>
          <p style="font-size:12px;color:#aaa;margin-top:16px;border-top:1px solid #eee;padding-top:12px;">
            若非本人操作，请忽略此邮件，您的账号密码不会被修改。
          </p>
        </div>
        """
        provider = get_cached_email_provider()
        provider.send_email(to_email, subject, html)

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
