#!/usr/bin/env python3
"""审计日志接口。"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies import get_audit_service, get_current_user, get_login_log_service
from src.api.response import success_response
from src.core.exceptions import NotFoundException
from src.schemas.auth import CurrentUserResponse
from src.schemas.audit import AuditLogResponse
from src.schemas.common import PaginatedResponse
from src.schemas.login_log import LoginLogResponse
from src.services.audit_service import AuditService
from src.services.login_log_service import LoginLogService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/logs",
    summary="审计日志列表",
    description="查询业务审计日志和登录日志",
)
async def list_audit_logs(
    request: Request,
    log_type: Literal["audit", "login", "all"] = Query(
        default="audit",
        alias="type",
        description="日志类型：audit 业务审计、login 登录日志、all 全部日志。",
    ),
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
    user_id: int | None = Query(default=None, description="登录日志的用户 ID。"),
    status: str | None = Query(default=None, description="登录日志结果，例如 success、failed。"),
    login_type: str | None = Query(default=None, description="登录方式，例如 password、sso。"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="每页返回的记录数，范围为 1-100。",
    ),
    audit_service: AuditService = Depends(get_audit_service),
    login_service: LoginLogService = Depends(get_login_log_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    fetch_page_size = page * page_size if log_type == "all" else page_size
    audit_result = audit_service.search(
        entity_type=entity_type,
        action=action,
        operator_id=operator_id,
        start_time=start_time,
        end_time=end_time,
        page=1 if log_type == "all" else page,
        page_size=fetch_page_size,
    ) if log_type in ("audit", "all") else {"items": [], "total": 0}
    login_result = login_service.search(
        user_id=user_id,
        status=status,
        login_type=login_type,
        start_time=start_time,
        end_time=end_time,
        page=1 if log_type == "all" else page,
        page_size=fetch_page_size,
    ) if log_type in ("login", "all") else {"items": [], "total": 0}

    if log_type == "all":
        items = sorted(
            [*audit_result["items"], *login_result["items"]],
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        start = (page - 1) * page_size
        items = items[start : start + page_size]
    else:
        result = audit_result if log_type == "audit" else login_result
        items = result["items"]

    total = audit_result["total"] + login_result["total"]
    page_result = PaginatedResponse[AuditLogResponse | LoginLogResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(
            (total + page_size - 1) // page_size
            if page_size > 0
            else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/logs/{log_id}",
    summary="审计日志详情",
    description="根据日志类型和 ID 查询单条日志详情",
)
async def get_audit_log(
    log_id: int,
    request: Request,
    log_type: Literal["audit", "login"] = Query(
        default="audit",
        alias="type",
        description="日志类型：audit 业务审计、login 登录日志。",
    ),
    audit_service: AuditService = Depends(get_audit_service),
    login_service: LoginLogService = Depends(get_login_log_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    result = (
        audit_service.get_by_id(log_id)
        if log_type == "audit"
        else login_service.get_by_id(log_id)
    )
    if result is None:
        raise NotFoundException(message=f"{log_type} 日志 {log_id} 不存在")
    response = (
        AuditLogResponse.model_validate(result)
        if log_type == "audit"
        else result
    )
    return success_response(response.model_dump(), request)
