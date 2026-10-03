#!/usr/bin/env python3
"""开放平台开发者认证业务逻辑。

- 注册 / 登录 / 修改密码 / 当前开发者解析（JWT）；
- 与管理端 AuthService 平行、分表（developers 表），令牌复用 core.tokens；
- 简化说明：本域第一版不做 Redis 服务端登录态（JWT 有效期内有效），
  登出由前端清理令牌实现；后续如需"踢下线/多端互斥"再引入登录态存储。

Classes:
    DeveloperAuthService: 开发者认证业务逻辑实现
"""

from __future__ import annotations

from datetime import datetime

from src.constants.constants import TOKEN_TTL_SECONDS
from src.constants.enums import DeveloperStatus
from src.core.exceptions import AuthenticationException, ConflictException
from src.core.tokens import create_access_token, decode_token
from src.models.entities.developer_entity import DeveloperEntity
from src.repositories.developer_repository import DeveloperRepository
from src.schemas.open.auth import (
    CurrentDeveloper,
    DeveloperProfileResponse,
    DeveloperTokenResponse,
)
from src.utils.security import hash_password, verify_password


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
        certification_type: str | None = None,
    ) -> DeveloperProfileResponse:
        """注册开发者账号。

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            confirm_password: 确认密码
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
            certification_type=certification_type,
            status=DeveloperStatus.ENABLED.value,
        )
        created = self._repository.create(entity)
        self._repository.commit()
        return self._to_profile(created)

    # ── 登录 ────────────────────────────────────────────

    def login(self, account: str, password: str) -> DeveloperTokenResponse:
        """开发者登录（账号=用户名或邮箱），成功签发访问令牌。"""
        dev = self._find_account(account)
        if dev is None or not verify_password(password, dev.password_hash or ""):
            raise AuthenticationException(message="用户名/邮箱或密码错误")
        if dev.status != DeveloperStatus.ENABLED.value:
            raise AuthenticationException(message="账号已被禁用")
        access_token = create_access_token(dev.id, extra_claims={"username": dev.username, "scope": "developer"})
        try:
            self._repository.update_last_login(dev.id, datetime.now())
            self._repository.commit()
        except Exception:  # noqa: BLE001
            self._repository.rollback()
        return DeveloperTokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=TOKEN_TTL_SECONDS,
        )

    # ── 当前开发者解析 ──────────────────────────────────

    def get_current_developer(self, authorization: str | None) -> CurrentDeveloper:
        """解析 Bearer 令牌，返回当前开发者。"""
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
        return CurrentDeveloper(
            id=dev.id,
            username=dev.username,
            email=dev.email,
            name=dev.name,
            phone=dev.phone,
            status=dev.status,
        )

    # ── 修改密码 ────────────────────────────────────────

    def change_password(self, developer_id: int, old_password: str, new_password: str) -> None:
        """修改密码：校验原密码后更新哈希。"""
        dev = self._repository.get_by_id(developer_id)
        if dev is None:
            raise AuthenticationException(message="开发者不存在")
        if not verify_password(old_password, dev.password_hash or ""):
            raise AuthenticationException(message="原密码不正确")
        dev.password_hash = hash_password(new_password)
        self._repository.commit()

    # ── 内部工具 ────────────────────────────────────────

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
