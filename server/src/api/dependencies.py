#!/usr/bin/env python3
"""
FastAPI 跨域公共依赖注入模块。

本文件只保留三个 API 域（管理系统 / 开放接口 / 开放平台门户）共享的依赖：
- get_request_id / get_pagination：请求级通用工具
- get_notification_dispatcher：站内信/通知分发器（多域复用）
- get_user_service / get_role_service / get_file_service：跨域共享业务服务工厂
  （服务本体位于 src/services/，由管理系统与开放接口两域复用）
- _bearer_scheme：HTTP Bearer 认证方案（管理端会话与开发者会话共用）

各域专属依赖已下沉：
- 管理系统：src/api/admin/dependencies.py
- 开放接口：src/api/open/dependencies.py
- 开放平台门户：src/api/open_portal/dependencies.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from src.infras.database import get_db_session
from src.schemas.common import PaginatedRequest

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher
    from src.services.file_service import FileStorageService
    from src.services.role_service import RoleService
    from src.services.user_service import UserService

# HTTP Bearer 认证方案（auto_error=False，缺失令牌时由 get_current_user / get_current_developer 统一抛 401）
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


def get_user_service(
    db_session: Session = Depends(get_db_session),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> UserService:
    """创建用户服务（管理系统 / 开放接口两域共用）。"""
    from src.repositories.role_repository import RoleRepository
    from src.repositories.user_repository import UserRepository
    from src.services.user_service import UserService

    return UserService(
        user_repository=UserRepository(session=db_session),
        role_repository=RoleRepository(session=db_session),
        dispatcher=dispatcher,
    )


def get_role_service(
    db_session: Session = Depends(get_db_session),
) -> RoleService:
    """创建角色服务（管理系统 / 开放接口两域共用）。"""
    from src.repositories.permission_repository import PermissionRepository
    from src.repositories.role_permission_repository import RolePermissionRepository
    from src.repositories.role_repository import RoleRepository
    from src.services.role_service import RoleService

    return RoleService(
        role_repository=RoleRepository(session=db_session),
        role_permission_repository=RolePermissionRepository(session=db_session),
        permission_repository=PermissionRepository(session=db_session),
    )


def get_file_service(
    db_session: Session = Depends(get_db_session),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> FileStorageService:
    """创建文件存储服务（管理系统 / 开放接口两域共用，StorageProvider 抽象层 + 请求级仓库）。"""
    from src.infras.storage import get_cached_storage_provider
    from src.repositories.file_repository import FileRepository
    from src.services.file_service import FileStorageService

    return FileStorageService(
        file_repository=FileRepository(session=db_session),
        provider=get_cached_storage_provider(),
        dispatcher=dispatcher,
    )
