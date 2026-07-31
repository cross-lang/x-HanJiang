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
from sqlalchemy.orm import Session

from src.core.container import Container
from src.infras.mysql import get_session_factory
from src.schemas.common import PaginatedRequest


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


def register_default_bindings(container: Container) -> None:
    """向 DI 容器注册默认组件。

    由 main.create_app 在应用启动时调用。
    """
    from src.core.container import Lifecycle
    from src.repositories.user_repository import UserRepository
    from src.services.user_service import UserService

    # Repository 与 Service 都是请求作用域（每次请求创建新实例，避免共享会话）
    container.register(UserRepository, UserRepository, Lifecycle.TRANSIENT)
    container.register(UserService, UserService, Lifecycle.TRANSIENT)
