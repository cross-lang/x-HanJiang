#!/usr/bin/env python3
"""审计日志接口。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    get_audit_service,
    get_current_user,
    get_login_log_service,
    is_admin_user,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.enums import AuditAction, LoginStatus, LoginType
from src.constants.permissions import PermissionAction, PermissionCode
from src.core.exceptions import NotFoundException
from src.schemas.audit import AuditLogResponse
from src.schemas.auth import CurrentUser
from src.services.admin.audit_service import AuditService
from src.services.admin.login_log_service import LoginLogService
from src.utils.csv import build_csv_stream_response

router = APIRouter(prefix="/audit", tags=["审计日志"])


def describe_audit_action(action: str) -> str:
    """审计动作中文展示：优先查 AuditAction（独有动作），再回退 PermissionAction。"""
    for enum_cls in (AuditAction, PermissionAction):
        for member in enum_cls:
            if member.mark == action:
                return member.desc
    return action


# ============================================================
# 业务审计日志（audit_logs 表）
# ============================================================
@router.get(
    "/logs",
    summary="业务审计日志列表",
    description="查询业务审计日志（数据变更记录）",
    dependencies=[Depends(require_user_permission(PermissionCode.AUDIT_LOG_VIEW.mark))],
)
@permission(PermissionCode.AUDIT_LOG_VIEW)
def list_audit_logs(
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
    keyword: str | None = Query(
        default=None,
        description="关键字，模糊匹配实体类型、操作、操作人、实体ID、IP、备注。",
    ),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始。"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，1-100。"),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    # 普通用户只能看自己的操作记录
    if not is_admin_user(current_user):
        operator_id = current_user.id
    result = audit_service.search(
        entity_type=entity_type,
        action=action,
        operator_id=operator_id,
        start_time=start_time,
        end_time=end_time,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = [AuditLogResponse.model_validate(i).model_dump() for i in result["items"]]
    user_ids = list({i["operator_id"] for i in items if i.get("operator_id")})
    user_map = audit_service.get_operator_names(user_ids)
    for i in items:
        u = user_map.get(i.get("operator_id"))
        i["operator_username"] = u["username"] if u else ""
        i["operator_real_name"] = u["name"] if u else ""
    result["items"] = items
    return success_response(result, request)


@router.get(
    "/logs/export",
    summary="导出审计日志",
    description="按筛选条件导出审计日志为 CSV 文件",
    dependencies=[Depends(require_user_permission(PermissionCode.AUDIT_LOG_EXPORT.mark))],
)
@permission(PermissionCode.AUDIT_LOG_EXPORT)
def export_audit_logs(
    entity_type: str | None = None,
    action: str | None = None,
    operator_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    audit_service: AuditService = Depends(get_audit_service),
):
    result = audit_service.search(
        entity_type=entity_type,
        action=action,
        operator_id=operator_id,
        start_time=start_time,
        end_time=end_time,
        page=1,
        page_size=100000,
    )
    # 批量查用户名
    user_ids = list({i.operator_id for i in result["items"] if i.operator_id})
    username_map = audit_service.get_operator_names(user_ids)
    fieldnames = [
        "id",
        "entity_type",
        "action",
        "operator_id",
        "operator_name",
        "ip_address",
        "created_at",
        "remarks",
    ]
    headers_cn = {
        "id": "ID",
        "entity_type": "实体类型",
        "action": "操作",
        "operator_id": "操作人ID",
        "operator_name": "操作人姓名",
        "ip_address": "IP",
        "created_at": "时间",
        "remarks": "备注",
    }
    csv_rows = []
    for row in result["items"]:
        data = AuditLogResponse.model_validate(row).model_dump()
        data["action"] = describe_audit_action(row.action)
        data["operator_id"] = row.operator_id or ""
        data["operator_name"] = username_map.get(row.operator_id, {}).get("name", "") if row.operator_id else ""
        csv_rows.append(data)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return build_csv_stream_response(
        fieldnames=fieldnames,
        headers_cn=headers_cn,
        rows=csv_rows,
        filename=f"audit_logs_{timestamp}.csv",
    )


@router.get(
    "/logs/{log_id}",
    summary="业务审计日志详情",
    description="根据 ID 查询单条业务审计日志详情",
    dependencies=[Depends(require_user_permission(PermissionCode.AUDIT_LOG_VIEW.mark))],
)
@permission(PermissionCode.AUDIT_LOG_VIEW)
def get_audit_log(
    log_id: int,
    request: Request,
    audit_service: AuditService = Depends(get_audit_service),
    _=Depends(get_current_user),
):
    result = audit_service.get_by_id(log_id)
    if result is None:
        raise NotFoundException(message=f"审计日志 {log_id} 不存在")
    data = AuditLogResponse.model_validate(result).model_dump()
    # 关联查用户名
    if result.operator_id:
        operator = audit_service.get_operator_names([result.operator_id]).get(result.operator_id)
        if operator:
            data["operator_username"] = operator["username"]
            data["operator_real_name"] = operator["name"]
    return success_response(data, request)


# ============================================================

# 登录日志（login_logs 表）

# ============================================================


@router.get(
    "/login-logs",
    summary="登录日志列表",
    description="查询登录日志",
    dependencies=[Depends(require_user_permission(PermissionCode.LOGIN_LOG_VIEW.mark))],
)
@permission(PermissionCode.LOGIN_LOG_VIEW)
def list_login_logs(
    request: Request,
    user_id: int | None = Query(default=None, description="用户 ID"),
    status: str | None = Query(default=None, description="登录结果：success / failed"),
    login_type: str | None = Query(default=None, description="登录方式：password / sso"),
    start_time: datetime | None = Query(default=None, description="查询起始时间"),
    end_time: datetime | None = Query(default=None, description="查询结束时间"),
    keyword: str | None = Query(
        default=None,
        description="关键字，模糊匹配IP、状态、登录方式。",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    login_service: LoginLogService = Depends(get_login_log_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    # 普通用户只能看自己的登录日志
    if not is_admin_user(current_user):
        user_id = current_user.id
    result = login_service.search(
        user_id=user_id,
        status=status,
        login_type=login_type,
        start_time=start_time,
        end_time=end_time,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return success_response(result, request)


@router.get(
    "/login-logs/export",
    summary="导出登录日志",
    description="按筛选条件导出登录日志为 CSV 文件",
    dependencies=[Depends(require_user_permission(PermissionCode.LOGIN_LOG_EXPORT.mark))],
)
@permission(PermissionCode.LOGIN_LOG_EXPORT)
def export_login_logs(
    request: Request,
    status: str | None = None,
    login_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    login_service: LoginLogService = Depends(get_login_log_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    user_id = None if is_admin_user(current_user) else current_user.id
    result = login_service.search(
        user_id=user_id,
        status=status,
        login_type=login_type,
        start_time=start_time,
        end_time=end_time,
        page=1,
        page_size=100000,
    )
    fieldnames = ["id", "username", "name", "ip_address", "status", "login_type", "created_at"]
    headers_cn = {
        "id": "ID",
        "username": "用户名",
        "name": "姓名",
        "ip_address": "IP",
        "status": "状态",
        "login_type": "登录方式",
        "created_at": "时间",
    }
    csv_rows = []
    for row in result["items"]:
        csv_rows.append(
            {
                "id": row.id,
                "username": row.username,
                "name": row.name or "",
                "ip_address": row.ip_address,
                "status": LoginStatus.get_desc_by_mark(row.status),
                "login_type": LoginType.get_desc_by_mark(row.login_type),
                "created_at": str(row.created_at),
            }
        )
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return build_csv_stream_response(
        fieldnames=fieldnames,
        headers_cn=headers_cn,
        rows=csv_rows,
        filename=f"login_logs_{timestamp}.csv",
    )


@router.get(
    "/login-logs/{log_id}",
    summary="登录日志详情",
    description="根据 ID 查询单条登录日志详情",
    dependencies=[Depends(require_user_permission(PermissionCode.LOGIN_LOG_VIEW.mark))],
)
@permission(PermissionCode.LOGIN_LOG_VIEW)
def get_login_log(
    log_id: int,
    request: Request,
    login_service: LoginLogService = Depends(get_login_log_service),
    _=Depends(get_current_user),
):
    result = login_service.get_detail(log_id)
    if result is None:
        raise NotFoundException(message=f"登录日志 {log_id} 不存在")
    return success_response(result.model_dump(), request)
