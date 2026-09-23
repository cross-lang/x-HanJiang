#!/usr/bin/env python3
"""
FastAPI 依赖注入模块

本模块定义了 API 层通用的 FastAPI Depends 依赖项工厂函数，
用于在路由处理函数中通过参数注入公共依赖。

Functions:
    get_request_id: 获取当前请求 ID
    get_pagination: 获取分页参数
    get_db_session: 获取数据库会话（FastAPI 依赖）
    get_user_service: 获取用户服务实例
"""

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.exceptions import AuthorizationException
from src.infras.email import EmailProvider, get_cached_email_provider
from src.infras.database import get_cached_database_provider
from src.schemas.auth import CurrentUserResponse
from src.schemas.common import PaginatedRequest
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.services.file_service import FileStorageService
from src.services.notification_dispatcher import NotificationDispatcher
from src.services.notification_service import NotificationService
from src.services.permission_service import PermissionService
from src.utils.helpers import get_client_ip

# HTTP Bearer 认证方案（auto_error=False，缺失令牌时由 get_current_user 统一抛 401）
_bearer_scheme = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str | None:
    """从请求状态中获取当前请求 ID。"""
    return getattr(request.state, "request_id", None)


def get_pagination(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedRequest:
    """获取分页参数。"""
    return PaginatedRequest(page=page, page_size=page_size)


def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话（FastAPI 依赖）。

    使用 FastAPI 的依赖注入机制管理数据库会话生命周期。
    确保每个请求都有独立的会话，并在请求结束后自动关闭。

    Yields:
        Session: 数据库会话对象
    """
    session_factory = get_cached_database_provider().get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取用户仓库实例（可被 DI 容器覆盖）。"""
    from src.repositories.user_repository import UserRepository

    return UserRepository(session=db_session)


def get_user_service(
    user_repository=Depends(get_user_repository),
):
    """使用当前请求的 Repository 创建用户服务。"""
    from src.services.user_service import UserService

    return UserService(user_repository=user_repository)


def get_email_provider() -> EmailProvider:
    """获取邮件发送基础设施实例。"""
    return get_cached_email_provider()


def get_alert_service(
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> AlertService:
    """获取告警服务实例。"""
    return AlertService(dispatcher=dispatcher)


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
    user_repository=Depends(get_user_repository),
    email_provider: EmailProvider = Depends(get_email_provider),
):
    """获取认证服务。"""
    notification_service = NotificationService(email_provider=email_provider)
    return AuthService(
        user_repository=user_repository,
        notification_service=notification_service,
    )


def get_role_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取角色仓库实例。"""
    from src.repositories.role_repository import RoleRepository

    return RoleRepository(session=db_session)


def get_permission_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取权限仓库实例。"""
    from src.repositories.permission_repository import PermissionRepository

    return PermissionRepository(session=db_session)


def get_role_permission_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取角色权限关联仓库实例。"""
    from src.repositories.role_permission_repository import RolePermissionRepository

    return RolePermissionRepository(session=db_session)


def get_login_log_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取登录日志仓库实例。"""
    from src.repositories.login_log_repository import LoginLogRepository

    return LoginLogRepository(session=db_session)


def get_role_service(
    role_repository=Depends(get_role_repository),
    role_permission_repository=Depends(get_role_permission_repository),
    permission_repository=Depends(get_permission_repository),
):
    """使用当前请求的 Repository 创建角色服务。"""
    from src.services.role_service import RoleService

    return RoleService(
        role_repository=role_repository,
        role_permission_repository=role_permission_repository,
        permission_repository=permission_repository,
    )


def get_permission_service(
    permission_repository=Depends(get_permission_repository),
    role_permission_repository=Depends(get_role_permission_repository),
    role_repository=Depends(get_role_repository),
):
    """使用当前请求的 Repository 创建权限服务。"""
    from src.services.permission_service import PermissionService

    return PermissionService(
        permission_repository=permission_repository,
        role_permission_repository=role_permission_repository,
        role_repository=role_repository,
    )


def get_login_log_service(
    login_log_repository=Depends(get_login_log_repository),
):
    """使用当前请求的 Repository 创建登录日志服务。"""
    from src.services.login_log_service import LoginLogService

    return LoginLogService(login_log_repository=login_log_repository)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUserResponse:
    """解析 Bearer 令牌，返回当前登录用户.

    使用 HTTPBearer 认证方案，Swagger UI 会自动在右上角显示 Authorize 按钮，
    并为所有依赖本函数的接口标注锁图标；点 Authorize 填一次令牌即可全局生效。
    """
    token = credentials.credentials if credentials is not None else None
    return auth_service.get_current_user(token)


def require_role(role_code: str):
    """要求当前用户必须属于指定角色。"""

    def dependency(
        current_user: CurrentUserResponse = Depends(get_current_user),
    ) -> CurrentUserResponse:
        if current_user.role_code != role_code and current_user.role_code != "super_admin":
            raise AuthorizationException(message=f"需要角色 {role_code}")
        return current_user

    return dependency


def require_permission(permission_code: str):
    """要求当前用户必须拥有指定权限。权限结果按角色缓存。"""

    def dependency(
        current_user: CurrentUserResponse = Depends(get_current_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> CurrentUserResponse:
        if not permission_service.has_permission(current_user.id, permission_code):
            raise AuthorizationException(message=f"缺少权限: {permission_code}")
        return current_user

    return dependency


def get_operator_context(
    current_user: CurrentUserResponse | None = None,
) -> dict[str, object]:
    """构造操作人上下文（供写操作审计/日志使用）。

    当前未启用强制鉴权，current_user 可能为 None，返回最小上下文。
    """
    if current_user is None:
        return {"operator_id": None, "operator_name": None}
    return {
        "operator_id": current_user.id,
        "operator_name": current_user.username,
    }


def get_notification_dispatcher(
    db_session: Session = Depends(get_db_session),
) -> NotificationDispatcher:
    """获取通知调度器实例。"""
    from src.infras.notification import get_registry

    return NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )



