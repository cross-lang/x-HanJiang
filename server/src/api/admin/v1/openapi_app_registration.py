#!/usr/bin/env python3
"""开放平台应用审批接口（管理端，独立于应用管理列表）。
路由前缀：/api/admin/v1/app-registrations
权限：OPENAPI_APP_APPROVE（查看与审批申请批次）
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_openapi_app_registration_service,
    get_user_operator_context,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.openapi_app_registration import (
    AppRegistrationApprovalRequest,
    AppRegistrationResponse,
)
from src.schemas.common import PaginatedResponse
from src.services.admin.openapi_app_registration_service import (
    OpenApiAppRegistrationService,
)

router = APIRouter(prefix="/app-registrations", tags=["管理系统：开放平台应用审批"])


@router.get(
    "",
    summary="应用申请列表",
    description="按批次展示开发者提交的创建/修改应用申请（最新申请在前），支持按类型、状态过滤与关键词搜索",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_APPROVE.mark))],
)
@permission(PermissionCode.OPENAPI_APP_APPROVE)
def list_registrations(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    registration_type: str | None = None,
    status: str | None = None,
    service: OpenApiAppRegistrationService = Depends(get_openapi_app_registration_service),
) -> JSONResponse:
    """分页查询应用申请批次，每行数据带申请ID。"""
    result = service.list_registrations(
        keyword=keyword,
        registration_type=registration_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[AppRegistrationResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"] if result["page_size"] > 0 else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/{registration_id}",
    summary="应用申请详情",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_APPROVE.mark))],
)
@permission(PermissionCode.OPENAPI_APP_APPROVE)
def get_registration(
    registration_id: int,
    request: Request,
    service: OpenApiAppRegistrationService = Depends(get_openapi_app_registration_service),
) -> JSONResponse:
    """按申请ID查询申请详情（含应用与申请人信息、申请快照、审批结果）。"""
    return success_response(service.get_registration(registration_id).model_dump(), request)


@router.put(
    "/{registration_id}/approval",
    summary="审批应用申请",
    description=(
        "通过/驳回一条应用申请；通过时 create 类置应用已授权、"
        "update 类将申请快照落地到应用表，驳回仅记录审批意见"
    ),
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_APPROVE.mark))],
)
@permission(PermissionCode.OPENAPI_APP_APPROVE)
def review_registration(
    registration_id: int,
    body: AppRegistrationApprovalRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: OpenApiAppRegistrationService = Depends(get_openapi_app_registration_service),
) -> JSONResponse:
    """审批一条应用申请（通过 / 驳回），审批结果同步站内信通知开发者。"""
    return success_response(
        service.review(
            registration_id,
            approved=body.approved,
            note=body.note,
            operator=get_user_operator_context(current_user, request),
        ).model_dump(),
        request,
    )
