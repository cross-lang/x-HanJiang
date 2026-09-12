#!/usr/bin/env python3
"""审计日志接口。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies import get_audit_service, get_current_user
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/logs",
    summary="审计日志列表",
    description="查询谁在什么时间改了什么数据的审计记录",
)
async def list_audit_logs(
    request: Request,
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    page: int = 1,
    page_size: int = 20,
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
    return success_response(result, request)
