#!/usr/bin/env python3
"""开放平台应用管理接口（内部管理员用，走用户态 JWT）。
路由前缀：/api/v1/admin/apps
权限：SUPERADMIN
注意：AppKey 明文只在创建 / 重置时返回一次，之后无法再查看。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.permission_decorator import permission
from src.api.dependencies import (
    get_current_user,
    get_openapi_app_service,
    get_user_operator_context,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.enums import AppOwnerType
from src.constants.permissions import PermissionCode
from src.schemas.admin.openapi_app import (
    OpenApiAppApprovalRequest,
    OpenApiAppCreatedResponse,
    OpenApiAppCreateRequest,
    OpenApiAppResponse,
    OpenApiAppScopesUpdateRequest,
    OpenApiAppStatusUpdateRequest,
    OpenApiAppUpdateRequest,
)
from src.schemas.common import PaginatedResponse
from src.services.admin.openapi_app_service import OpenApiAppService

router = APIRouter(prefix="/admin/apps", tags=["开放平台应用管理"])


@router.get(
    "/scopes",
    summary="可用 scope 列表",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_SCOPE_VIEW.mark))],
)
@permission(PermissionCode.OPENAPI_SCOPE_VIEW)
def list_scopes(
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
) -> JSONResponse:
    """返回所有可用的开放平台 scope（分组展示给前端创建应用时勾选）。"""
    return success_response(service.list_scopes(), request)


@router.post(
    "",
    summary="创建开放应用",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_CREATE.mark))],
)
@permission(PermissionCode.OPENAPI_APP_CREATE)
def create_app(
    body: OpenApiAppCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    """创建开放应用。
    响应里的 app_key 仅本次返回，之后无法再查看。
    """
    resp, app_key = service.create_app(
        name=body.name,
        description=body.description,
        scopes=body.scopes,
        rate_limit_per_minute=body.rate_limit_per_minute,
        auth_mode=body.auth_mode,
        owner_type=AppOwnerType.ADMIN.value,
        owner_id=current_user.id,
        operator=get_user_operator_context(current_user, request),
    )
    data = OpenApiAppCreatedResponse(**resp.model_dump(), app_key=app_key).model_dump()
    return success_response(data, request, code=201)


@router.get(
    "",
    summary="应用列表",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_VIEW.mark))],
)
@permission(PermissionCode.OPENAPI_APP_VIEW)
def list_apps(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    owner_type: str | None = None,
    scope: str | None = None,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    """返回分页应用列表，结构与用户列表等接口一致：{items, total, page, page_size}。

    scope 管理端个人视角类目：
      created  = 我新建的（管理员创建且归属本人）
      approved = 我审批的（待审批 pending ∪ 审批人 approved_by=当前用户）
    """
    result = service.list_apps(
        keyword=keyword,
        owner_type=owner_type,
        scope=scope,
        operator_id=current_user.id if scope in ("created", "approved") else None,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[OpenApiAppResponse](
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
    "/{app_id}",
    summary="应用详情",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_VIEW.mark))],
)
@permission(PermissionCode.OPENAPI_APP_VIEW)
def get_app(
    app_id: int,
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    return success_response(service.get_by_id(app_id).model_dump(), request)


@router.put(
    "/{app_id}",
    summary="更新应用",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_EDIT.mark))],
)
@permission(PermissionCode.OPENAPI_APP_EDIT)
def update_app(
    app_id: int,
    body: OpenApiAppUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    return success_response(
        service.update(
            app_id,
            body.model_dump(exclude_unset=True),
            operator=get_user_operator_context(current_user, request),
        ).model_dump(),
        request,
    )


@router.put(
    "/{app_id}/scopes",
    summary="更新应用 scope",
    description="覆盖更新应用的 scope 列表（授权操作，独立于编辑权限）；传入的 scopes 会完全覆盖原有值",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_SCOPES.mark))],
)
@permission(PermissionCode.OPENAPI_APP_SCOPES)
def update_app_scopes(
    app_id: int,
    body: OpenApiAppScopesUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    """覆盖更新应用的 scope 列表。传入的 scopes 会完全覆盖原有值。"""
    return success_response(
        service.update_scopes(
            app_id,
            body.scopes,
            operator=get_user_operator_context(current_user, request),
        ).model_dump(),
        request,
    )


@router.put(
    "/{app_id}/approval",
    summary="审批开发者 scope 申请",
    description="通过/驳回开发者提交的 scope 申请并记录审批意见；通过仅置状态，scope 目标值由开发者申请端点写入",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_SCOPES.mark))],
)
@permission(PermissionCode.OPENAPI_APP_SCOPES)
def update_app_approval(
    app_id: int,
    body: OpenApiAppApprovalRequest,
    request: Request,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    return success_response(
        service.update_approval(
            app_id,
            approved=body.approved,
            note=body.note,
            operator=get_user_operator_context(current_user, request),
        ).model_dump(),
        request,
    )


@router.put(
    "/{app_id}/status",
    summary="启用/禁用应用",
    description="切换应用生效状态；禁用后该应用的全部 API 调用立即被拒绝",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_STATUS.mark))],
)
@permission(PermissionCode.OPENAPI_APP_STATUS)
def update_app_status(
    app_id: int,
    body: OpenApiAppStatusUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    """启用或禁用应用（独立于通用更新，单独权限控制）。"""
    return success_response(
        service.update_status(
            app_id,
            body.status,
            operator=get_user_operator_context(current_user, request),
        ).model_dump(),
        request,
    )


@router.post(
    "/{app_id}/rotate-key",
    summary="重置 AppKey",
    description="旧 Key 立即失效，该应用所有使用旧 Key 的调用都会失败；独立于编辑权限",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_ROTATE_KEY.mark))],
)
@permission(PermissionCode.OPENAPI_APP_ROTATE_KEY)
def rotate_key(
    app_id: int,
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    resp, new_key = service.rotate_key(app_id)
    return success_response(
        {**resp.model_dump(), "app_key": new_key, "warning": "新 AppKey 仅本次返回"},
        request,
    )


@router.delete(
    "/{app_id}",
    summary="删除应用",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_APP_DELETE.mark))],
)
@permission(PermissionCode.OPENAPI_APP_DELETE)
def delete_app(
    app_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    ok = service.delete(app_id, operator=get_user_operator_context(current_user, request))
    return success_response({"deleted": ok}, request)
