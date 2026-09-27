#!/usr/bin/env python3
"""审计日志接口。"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from src.api.api_permission_decorator import permission
from src.api.dependencies import get_audit_service, get_current_user, get_login_log_service, require_user_permission
from src.api.response import success_response
from src.core.exceptions import NotFoundException
from src.schemas.audit import AuditLogResponse
from src.services.audit_service import AuditService
from src.services.login_log_service import LoginLogService

router = APIRouter(prefix="/audit", tags=["审计日志"])


# ============================================================
# 业务审计日志（audit_logs 表）
# ============================================================


@router.get(
    "/logs",
    summary="业务审计日志列表",
    description="查询业务审计日志（数据变更记录）",
    dependencies=[Depends(require_user_permission("audit_log:view"))],
)
@permission("audit_log:view", "查看审计日志", "audit_log", "view")
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
        description="查询起始时间，格式为 ISO 8601，例如 2026-09-01T00:00:00。",
    ),
    end_time: datetime | None = Query(
        default=None,
        description="查询结束时间，格式为 ISO 8601，例如 2026-09-13T23:59:59。",
    ),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，1-100。"),
    audit_service: AuditService = Depends(get_audit_service),
    _=Depends(get_current_user),
):
    result = audit_service.search(
        entity_type=entity_type,
        action=action,
        operator_id=operator_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    result["items"] = [AuditLogResponse.model_validate(i).model_dump() for i in result["items"]]
    return success_response(result, request)



@router.get(
    "/logs/export",
    summary="导出审计日志",
    description="按筛选条件导出审计日志为 CSV 文件",
    dependencies=[Depends(require_user_permission("audit_log:export"))],
)
@permission("audit_log:export", "导出审计日志", "audit_log", "export")
async def export_audit_logs(
    entity_type: str | None = None,
    action: str | None = None,
    operator_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    audit_service: AuditService = Depends(get_audit_service),
):
    result = audit_service.search(
        entity_type=entity_type, action=action, operator_id=operator_id,
        start_time=start_time, end_time=end_time, page=1, page_size=100000,
    )

    fieldnames = ["id", "entity_type", "entity_id", "action", "operator_name", "ip_address", "created_at", "remarks"]
    headers_cn = {
        "id": "ID", "entity_type": "实体类型", "entity_id": "实体ID", "action": "操作",
        "operator_name": "操作人", "ip_address": "IP", "created_at": "时间", "remarks": "备注",
    }

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writerow(headers_cn)
    for row in result["items"]:
        data = AuditLogResponse.model_validate(row).model_dump()
        writer.writerow({k: data.get(k, "") for k in fieldnames})

    content = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs_export.csv"},
    )


@router.get(
    "/logs/{log_id}",
    summary="业务审计日志详情",
    description="根据 ID 查询单条业务审计日志详情",
    dependencies=[Depends(require_user_permission("audit_log:view"))],
)
@permission("audit_log:view", "查看审计日志", "audit_log", "view")
async def get_audit_log(
    log_id: int,
    request: Request,
    audit_service: AuditService = Depends(get_audit_service),
    _=Depends(get_current_user),
):
    result = audit_service.get_by_id(log_id)
    if result is None:
        raise NotFoundException(message=f"审计日志 {log_id} 不存在")
    return success_response(AuditLogResponse.model_validate(result).model_dump(), request)



# ============================================================
# 登录日志（login_logs 表）
# ============================================================


@router.get(
    "/login-logs",
    summary="登录日志列表",
    description="查询登录日志",
    dependencies=[Depends(require_user_permission("login_log:view"))],
)
@permission("login_log:view", "查看登录日志", "login_log", "view")
async def list_login_logs(
    request: Request,
    user_id: int | None = Query(default=None, description="用户 ID"),
    status: str | None = Query(default=None, description="登录结果：success / failed"),
    login_type: str | None = Query(default=None, description="登录方式：password / sso"),
    start_time: datetime | None = Query(default=None, description="查询起始时间"),
    end_time: datetime | None = Query(default=None, description="查询结束时间"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    login_service: LoginLogService = Depends(get_login_log_service),
    _=Depends(get_current_user),
):
    result = login_service.search(
        user_id=user_id,
        status=status,
        login_type=login_type,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return success_response(result, request)


@router.get(
    "/login-logs/{log_id}",
    summary="登录日志详情",
    description="根据 ID 查询单条登录日志详情",
    dependencies=[Depends(require_user_permission("login_log:view"))],
)
@permission("login_log:view", "查看登录日志", "login_log", "view")
async def get_login_log(
    log_id: int,
    request: Request,
    login_service: LoginLogService = Depends(get_login_log_service),
    _=Depends(get_current_user),
):
    result = login_service.get_by_id(log_id)
    if result is None:
        raise NotFoundException(message=f"登录日志 {log_id} 不存在")
    return success_response(result.model_dump(), request)
