#!/usr/bin/env python3
"""
FastAPI 依赖注入模块

本模块定义了 API 层通用的 FastAPI Depends 依赖项工厂函数，
用于在路由处理函数中通过参数注入公共依赖。
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from time import time
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.constants.constants import (
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_AUTHORIZATION,
    OPENAPI_HEADER_DATE,
)
from src.core.exceptions import AuthorizationException
from src.infras.database import get_cached_database_provider, get_db_session
from src.schemas.auth import CurrentUser
from src.schemas.openapi_app import CurrentApp
from src.schemas.common import PaginatedRequest
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.services.file_service import FileStorageService
from src.services.maintenance_service import MaintenanceService
from src.services.notification_service import NotificationService
from src.services.permission_service import PermissionService
from src.utils.helpers import get_client_ip

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher
    from src.repositories.audit_log_repository import AuditLogRepository
    from src.repositories.login_log_repository import LoginLogRepository
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.repositories.permission_repository import PermissionRepository
    from src.repositories.role_permission_repository import RolePermissionRepository
    from src.repositories.role_repository import RoleRepository
    from src.repositories.user_repository import UserRepository
    from src.services.login_log_service import LoginLogService
    from src.services.openapi_app_service import OpenApiAppService
    from src.services.role_service import RoleService
    from src.services.user_service import UserService

# HTTP Bearer 认证方案（auto_error=False，缺失令牌时由 get_current_user 统一抛 401）
_bearer_scheme = HTTPBearer(auto_error=False)

# 开放平台 API Key 认证方案（Swagger UI 右上角会出现 Authorize 按钮）
_app_id_scheme = APIKeyHeader(name=OPENAPI_HEADER_APP_ID, scheme_name="OpenAppId", auto_error=False)
_app_key_scheme = APIKeyHeader(name=OPENAPI_HEADER_APP_KEY, scheme_name="OpenAppKey", auto_error=False)
_app_date_scheme = APIKeyHeader(name=OPENAPI_HEADER_DATE, scheme_name="OpenAppDate", auto_error=False)
_app_auth_scheme = APIKeyHeader(name=OPENAPI_HEADER_AUTHORIZATION, scheme_name="OpenAppAuthorization", auto_error=False)


def get_request_id(request: Request) -> str | None:
    """从请求状态中获取当前请求 ID。"""
    return getattr(request.state, "request_id", None)


def get_pagination(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedRequest:
    """获取分页参数。"""
    return PaginatedRequest(page=page, page_size=page_size)


def get_notification_dispatcher(
    db_session: Session = Depends(get_db_session),
) -> NotificationDispatcher:
    """获取通知调度器实例（供 AlertService 等内部服务使用）。"""
    from src.infras.notification import get_registry
    from src.notification.dispatcher import NotificationDispatcher

    return NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )


def get_notification_service(
    db_session: Session = Depends(get_db_session),
) -> NotificationService:
    """获取通知业务服务实例。"""
    from src.infras.notification import get_registry
    from src.notification.dispatcher import NotificationDispatcher

    dispatcher = NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )
    return NotificationService(
        dispatcher=dispatcher,
        session=db_session,
    )


def get_user_repository(
    db_session: Session = Depends(get_db_session),
) -> UserRepository:
    """获取用户仓库实例（可被 DI 容器覆盖）。"""
    from src.repositories.user_repository import UserRepository

    return UserRepository(session=db_session)


def get_login_log_repository(
    db_session: Session = Depends(get_db_session),
) -> LoginLogRepository:
    """获取登录日志仓库实例。"""
    from src.repositories.login_log_repository import LoginLogRepository

    return LoginLogRepository(session=db_session)


def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> UserService:
    """使用当前请求的 Repository 创建用户服务。"""
    from src.services.user_service import UserService

    return UserService(user_repository=user_repository, dispatcher=dispatcher)


def get_alert_service(
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    db_session: Session = Depends(get_db_session),
) -> AlertService:
    """获取告警服务实例。"""
    return AlertService(dispatcher=dispatcher, session=db_session)


def get_audit_service(
    db_session: Session = Depends(get_db_session),
) -> AuditService:
    """获取审计服务。"""
    from src.repositories.audit_log_repository import AuditLogRepository

    return AuditService(audit_log_repository=AuditLogRepository(session=db_session))


@lru_cache(maxsize=1)
def get_file_service() -> FileStorageService:
    """获取共享的文件存储服务，使用 StorageProvider 抽象层。"""
    from src.infras.storage import get_cached_storage_provider

    return FileStorageService(provider=get_cached_storage_provider())


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    login_log_repository: LoginLogRepository = Depends(get_login_log_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> AuthService:
    """获取认证服务。"""
    return AuthService(
        user_repository=user_repository,
        login_log_repository=login_log_repository,
        dispatcher=dispatcher,
    )


def get_role_repository(
    db_session: Session = Depends(get_db_session),
) -> RoleRepository:
    """获取角色仓库实例。"""
    from src.repositories.role_repository import RoleRepository

    return RoleRepository(session=db_session)


def get_permission_repository(
    db_session: Session = Depends(get_db_session),
) -> PermissionRepository:
    """获取权限仓库实例。"""
    from src.repositories.permission_repository import PermissionRepository

    return PermissionRepository(session=db_session)


def get_role_permission_repository(
    db_session: Session = Depends(get_db_session),
) -> RolePermissionRepository:
    """获取角色权限关联仓库实例。"""
    from src.repositories.role_permission_repository import RolePermissionRepository

    return RolePermissionRepository(session=db_session)


def get_role_service(
    role_repository: RoleRepository = Depends(get_role_repository),
    role_permission_repository: RolePermissionRepository = Depends(get_role_permission_repository),
    permission_repository: PermissionRepository = Depends(get_permission_repository),
) -> RoleService:
    """使用当前请求的 Repository 创建角色服务。"""
    from src.services.role_service import RoleService

    return RoleService(
        role_repository=role_repository,
        role_permission_repository=role_permission_repository,
        permission_repository=permission_repository,
    )


def get_permission_service(
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    role_permission_repository: RolePermissionRepository = Depends(get_role_permission_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> PermissionService:
    """使用当前请求的 Repository 创建权限服务。"""
    from src.services.permission_service import PermissionService

    return PermissionService(
        permission_repository=permission_repository,
        role_permission_repository=role_permission_repository,
        role_repository=role_repository,
        dispatcher=dispatcher,
    )


def get_login_log_service(
    login_log_repository: LoginLogRepository = Depends(get_login_log_repository),
) -> LoginLogService:
    """使用当前请求的 Repository 创建登录日志服务。"""
    from src.services.login_log_service import LoginLogService

    return LoginLogService(login_log_repository=login_log_repository)


def get_openapi_app_service(
    db_session: Session = Depends(get_db_session),
) -> OpenApiAppService:
    """创建开放平台应用管理服务。"""
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.openapi_app_service import OpenApiAppService

    return OpenApiAppService(repo=OpenApiAppRepository(session=db_session))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    """解析 Bearer 令牌，返回当前登录用户."""
    token = credentials.credentials if credentials is not None else None
    return auth_service.get_current_user(token)


def require_user_role(role_code: str):
    """要求当前用户必须属于指定角色。"""

    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role_code != role_code and current_user.role_code != "super_admin":
            raise AuthorizationException(message=f"需要角色 {role_code}")
        return current_user

    return dependency


def require_user_permission(permission_code: str):
    """要求当前用户必须拥有指定权限。权限结果按角色缓存。"""

    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> CurrentUser:
        if not permission_service.has_permission(current_user.id, permission_code):
            raise AuthorizationException(message=f"缺少权限: {permission_code}")
        return current_user

    return dependency


def get_user_operator_context(current_user: CurrentUser) -> dict[str, object]:
    """构造用户态操作人上下文（供写操作审计/日志使用）。"""
    return {
        "operator_id": current_user.id,
        "operator_name": current_user.username,
    }


# ============================================================
# 面向应用（开放平台）鉴权
# ============================================================


def get_app_operator_context(app: CurrentApp) -> dict[str, object]:
    """构造应用态操作人上下文（供写操作审计/日志使用）。"""
    return {
        "operator_id": app.app_id,
        "operator_name": app.name,
    }


async def get_current_app(
    request: Request,
    _app_id: str | None = Depends(_app_id_scheme),
    _app_key: str | None = Depends(_app_key_scheme),
    _app_date: str | None = Depends(_app_date_scheme),
    _app_auth: str | None = Depends(_app_auth_scheme),
    service: OpenApiAppService = Depends(get_openapi_app_service),
) -> CurrentApp:
    """解析开放平台应用身份，委托给 OpenApiAppService。"""
    current = await service.authenticate(request)
    request.state.current_app = current
    return current


def require_app_scope(scope: str):
    """要求当前应用必须拥有指定 scope。"""

    def dependency(app: CurrentApp = Depends(get_current_app)) -> CurrentApp:
        if scope not in app.scopes:
            raise AuthorizationException(message=f"应用缺少 scope: {scope}")
        return app

    return dependency
