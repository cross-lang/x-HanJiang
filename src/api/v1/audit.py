#!/usr/bin/env python3
"""审计日志接口。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies import get_audit_service, get_current_user
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.schemas.audit import AuditLogResponse
from src.schemas.common import PaginatedResponse
from src.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/logs",
    summary="审计日志列表",
    description="查询谁在什么时间改了什么数据的审计记录",
)
async def list_audit_logs(
    request: Request,
    entity_type: str | None = Query(
        default=None,
        description="被操作的数据类型，例如 user、role、permission。留空表示查询全部类型。",
    ),
    action: str | None = Query(
        default=None,
        description="操作类型，例如 create、update、delete。留空表示查询全部操作。",
    ),
    operator_id: int | None = Query(
        default=None,
        description="操作人用户 ID，只查询指定用户产生的审计记录。",
    ),
    start_time: datetime | None = Query(
        default=None,
        description="查询起始时间，包含该时间点，格式为 ISO 8601，例如 2026-09-01T00:00:00。",
    ),
    end_time: datetime | None = Query(
        default=None,
        description="查询结束时间，包含该时间点，格式为 ISO 8601，例如 2026-09-13T23:59:59。",
    ),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="每页返回的记录数，范围为 1-100。",
    ),
    service: AuditService = Depends(get_audit_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    result = service.search(
        entity_type=entity_type,
        action=action,
        operator_id=operator_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[AuditLogResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"]
            if result["page_size"] > 0
            else 0
        ),
    )
    return success_response(page_result.model_dump(), request)
