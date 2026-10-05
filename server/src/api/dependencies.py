#!/usr/bin/env python3
"""
FastAPI 跨域公共依赖注入模块。

本文件只保留三个 API 域（管理系统 / 开放接口 / 开放平台门户）共享的依赖：
- get_request_id / get_pagination：请求级通用工具
- get_notification_dispatcher：站内信/通知分发器（多域复用）
- _bearer_scheme：HTTP Bearer 认证方案（管理端会话与开发者会话共用）

各域专属依赖已下沉：
- 管理系统：src/api/admin/dependencies.py
- 开放接口：src/api/open/dependencies.py
- 开放平台门户：src/api/open_portal/dependencies.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.infras.database import get_db_session
from src.schemas.common import PaginatedRequest

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher

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
