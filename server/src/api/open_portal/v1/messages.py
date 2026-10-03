#!/usr/bin/env python3
"""开放平台门户：开发者站内信接口。
路由前缀：/api/open-portal/v1/messages
鉴权：门户会话 JWT（get_current_developer），与管理端站内信（/api/v1/station/messages）分表隔离。
"""

from fastapi import APIRouter, Depends, Path, Query, Request

from src.api.dependencies import (
    get_current_developer,
    get_developer_message_service,
)
from src.api.response import success_response
from src.schemas.common import PaginatedResponse
from src.schemas.open_portal.auth import CurrentDeveloper
from src.schemas.open_portal.message import DeveloperMessageCountResponse, DeveloperMessageResponse
from src.services.open_portal.developer_message_service import DeveloperMessageService

router = APIRouter(prefix="/messages", tags=["开放平台门户：站内信"])


@router.get(
    "/unread-count",
    summary="未读消息数",
    response_model=DeveloperMessageCountResponse,
)
def unread_count(
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperMessageService = Depends(get_developer_message_service),
):
    count = service.unread_count(current_developer.id)
    return success_response({"count": count}, request)


@router.get(
    "",
    summary="我的站内信列表",
    response_model=PaginatedResponse[DeveloperMessageResponse],
)
def my_messages(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页记录数"),
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperMessageService = Depends(get_developer_message_service),
):
    data = service.list_messages(current_developer.id, page, page_size)
    return success_response(data, request)


@router.post(
    "/{msg_id}/read",
    summary="标记单条已读",
)
def mark_read(
    msg_id: int = Path(ge=1, description="消息 ID"),
    request: Request = ...,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperMessageService = Depends(get_developer_message_service),
):
    service.mark_read(current_developer.id, msg_id)
    return success_response({"message": "已标记已读"}, request)


@router.post(
    "/read-all",
    summary="全部已读",
)
def mark_all_read(
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperMessageService = Depends(get_developer_message_service),
):
    service.mark_all_read(current_developer.id)
    return success_response({"message": "全部已读"}, request)
