#!/usr/bin/env python3
"""站内信接口。"""

from fastapi import APIRouter, Depends, Query, Request

from src.api.admin.permission_decorator import permission
from src.api.dependencies import (
    CurrentUser,
    get_current_user,
    get_station_service,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.services.admin.station_service import StationMessageService

router = APIRouter(prefix="/station/messages", tags=["站内信"])


@router.get(
    "/unread-count",
    summary="未读消息数",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_VIEW.mark))],
)
@permission(PermissionCode.STATION_VIEW)
def unread_count(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
):
    count = service.unread_count(current_user.id)
    return success_response({"count": count}, request)


@router.get(
    "",
    summary="我的消息列表",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_VIEW.mark))],
)
@permission(PermissionCode.STATION_VIEW)
def my_messages(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
):
    data = service.list_messages(current_user.id, page, page_size)
    return success_response(data, request)


@router.post(
    "/{msg_id}/read",
    summary="标记单条已读",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_EDIT.mark))],
)
@permission(PermissionCode.STATION_EDIT)
def mark_read(
    msg_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
):
    service.mark_read(current_user.id, msg_id)
    return success_response({"message": "已标记已读"}, request)


@router.post(
    "/read-all",
    summary="全部已读",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_EDIT.mark))],
)
@permission(PermissionCode.STATION_EDIT)
def mark_all_read(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
):
    service.mark_all_read(current_user.id)
    return success_response({"message": "全部已读"}, request)
