#!/usr/bin/env python3
"""站内信接口。

提供当前登录用户的站内信收件箱能力：
未读数 / 分页列表（来源、日期区间、关键词过滤）/ 详情 / 标记已读 / 全部已读 / CSV 导出。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_station_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.services.admin.station_service import StationMessageService
from src.utils.csv import build_csv_stream_response

router = APIRouter(prefix="/station/messages", tags=["管理系统：站内信"])


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
) -> JSONResponse:
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
    source: str | None = Query(default=None, description="来源过滤（system_notice/station/alert/openapi_app）"),
    start_date: datetime | None = Query(default=None, description="接收起始时间（含）"),
    end_date: datetime | None = Query(default=None, description="接收截止时间（含）"),
    keyword: str | None = Query(default=None, description="关键词（模糊匹配标题/正文）"),
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
) -> JSONResponse:
    data = service.list_messages(
        current_user.id,
        page,
        page_size,
        source=source,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
    )
    return success_response(data, request)


@router.get(
    "/recent",
    summary="最近站内信（铃铛下拉）",
    description="查询最近 N 条站内信并返回未读数（一次请求，替代未读数+列表两次请求）",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_VIEW.mark))],
)
@permission(PermissionCode.STATION_VIEW)
def recent_messages(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="最近条数"),
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
) -> JSONResponse:
    data = service.list_recent(current_user.id, limit)
    return success_response(data, request)


@router.get(
    "/export",
    summary="导出我的消息（CSV）",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_VIEW.mark))],
)
@permission(PermissionCode.STATION_VIEW)
def export_messages(
    request: Request,
    source: str | None = Query(default=None, description="来源过滤"),
    start_date: datetime | None = Query(default=None, description="接收起始时间（含）"),
    end_date: datetime | None = Query(default=None, description="接收截止时间（含）"),
    keyword: str | None = Query(default=None, description="关键词过滤"),
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
) -> StreamingResponse:
    rows = service.export_rows(
        current_user.id,
        source=source,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
    )
    fieldnames = ["id", "title", "content", "event_type", "source", "status", "created_at", "read_at"]
    headers_cn = {
        "id": "ID",
        "title": "标题",
        "content": "内容",
        "event_type": "事件类型",
        "source": "来源",
        "status": "状态",
        "created_at": "接收时间",
        "read_at": "已读时间",
    }
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return build_csv_stream_response(
        fieldnames=fieldnames,
        headers_cn=headers_cn,
        rows=rows,
        filename=f"站内信-{timestamp}.csv",
    )


@router.get(
    "/{msg_id}",
    summary="消息详情",
    dependencies=[Depends(require_user_permission(PermissionCode.STATION_VIEW.mark))],
)
@permission(PermissionCode.STATION_VIEW)
def message_detail(
    msg_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: StationMessageService = Depends(get_station_service),
) -> JSONResponse:
    detail = service.get_message_detail(current_user.id, msg_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="站内信不存在")
    return success_response(detail, request)


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
) -> JSONResponse:
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
) -> JSONResponse:
    service.mark_all_read(current_user.id)
    return success_response({"message": "全部已读"}, request)
