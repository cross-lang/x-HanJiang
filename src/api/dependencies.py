#!/usr/bin/env python3
"""
FastAPI 依赖注入模块

本模块定义了 API 层通用的 FastAPI Depends 依赖项工厂函数，
用于在路由处理函数中通过参数注入公共依赖。

Functions:
    get_request_id: 获取当前请求 ID
    get_container: 获取 DI 容器实例
    get_pagination: 获取分页参数
    get_db_session: 获取数据库会话（FastAPI 依赖）
    get_user_service: 获取用户服务实例
"""

from collections.abc import Generator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.container import Container
from src.infras.mysql import get_session_factory
from src.schemas.auth import CurrentUserResponse
from src.schemas.common import PaginatedRequest
from src.services.auth_service import AuthService

# HTTP Bearer 认证方案（auto_error=False，缺失令牌时由 get_current_user 统一抛 401）
_bearer_scheme = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str | None:
    """从请求状态中获取当前请求 ID。"""
    return getattr(request.state, "request_id", None)


def get_container() -> Container:
    """获取全局 DI 容器实例。

    用于在 endpoint 中按需获取已注册的组件（如缓存、外部服务等）。
    """
    return Container.get_instance()


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
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_client_ip(request: Request) -> str | None:
    """获取客户端真实 IP（优先代理头）。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取用户仓库实例（可被 DI 容器覆盖）。"""
    from src.repositories.user_repository import UserRepository

    return UserRepository(session=db_session)


def get_user_service(
    user_repository=Depends(get_user_repository),
):
    """获取用户服务实例。

    通过 DI 容器优先解析；如果未注册，则回退到手写构造（兼容旧调用）。
    """
    from src.services.user_service import UserService

    container = Container.get_instance()
    try:
        return container.resolve(UserService)
    except Exception:
        # DI 未注册时退回到直接构造
        return UserService(user_repository=user_repository)


def get_auth_service(
    user_repository=Depends(get_user_repository),
):
    """获取认证服务实例。"""
    container = Container.get_instance()
    try:
        return container.resolve(AuthService)
    except Exception:
        return AuthService(user_repository=user_repository)


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
    """获取角色服务实例。"""
    from src.services.role_service import RoleService

    container = Container.get_instance()
    try:
        return container.resolve(RoleService)
    except Exception:
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
    """获取权限服务实例。"""
    from src.services.permission_service import PermissionService

    container = Container.get_instance()
    try:
        return container.resolve(PermissionService)
    except Exception:
        return PermissionService(
            permission_repository=permission_repository,
            role_permission_repository=role_permission_repository,
            role_repository=role_repository,
        )


def get_login_log_service(
    login_log_repository=Depends(get_login_log_repository),
):
    """获取登录日志服务实例。"""
    from src.services.login_log_service import LoginLogService

    container = Container.get_instance()
    try:
        return container.resolve(LoginLogService)
    except Exception:
        return LoginLogService(login_log_repository=login_log_repository)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUserResponse:
    """解析 Bearer 令牌，返回当前登录用户。

    使用 HTTPBearer 认证方案，Swagger UI 会自动在右上角显示 Authorize 按钮，
    并为所有依赖本函数的接口标注锁图标；点 Authorize 填一次令牌即可全局生效。
    """
    token = credentials.credentials if credentials is not None else None
    return auth_service.get_current_user(token)


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


def register_default_bindings(container: Container) -> None:
    """向 DI 容器注册默认组件。

    由 main.create_app 在应用启动时调用。
    """
    from src.core.container import Lifecycle
    from src.repositories.user_repository import UserRepository
    from src.services.auth_service import AuthService
    from src.services.user_service import UserService

    # Repository 与 Service 都是请求作用域（每次请求创建新实例，避免共享会话）
    container.register(UserRepository, UserRepository, Lifecycle.TRANSIENT)
    container.register(UserService, UserService, Lifecycle.TRANSIENT)
    container.register(AuthService, AuthService, Lifecycle.TRANSIENT)
