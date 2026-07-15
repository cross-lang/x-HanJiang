#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from typing import Generator, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.schemas.common import PaginatedRequest
from src.core.container import Container
from src.infra.database import get_session_factory


def get_request_id(request: Request) -> Optional[str]:
    """从请求状态中获取当前请求 ID。

    Args:
        request: FastAPI 请求对象

    Returns:
        Optional[str]: 请求追踪 ID
    """
    return getattr(request.state, "request_id", None)


def get_container() -> Container:
    """获取全局 DI 容器实例。

    Returns:
        Container: 全局依赖注入容器
    """
    return Container.get_instance()


def get_pagination(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedRequest:
    """获取分页参数。

    Args:
        page: 页码（从 1 开始）
        page_size: 每页记录数

    Returns:
        PaginatedRequest: 分页请求参数
    """
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


def get_user_service(
    db_session: Session = Depends(get_db_session),
):
    """获取用户服务实例。

    每次请求创建新的 UserRepository 和 UserService 实例，注入数据库会话。

    Args:
        db_session: 数据库会话（通过 FastAPI Depends 自动注入）

    Returns:
        UserService: 用户业务逻辑实例
    """
    from src.repositories.user_repository import UserRepository
    from src.services.user_service import UserService

    user_repository = UserRepository(session=db_session)
    return UserService(user_repository=user_repository)