#!/usr/bin/env python3
"""开放平台开发者用户管理接口（内部管理员用，走用户态 JWT）。

路由前缀：/api/admin/v1/developers
权限：
- openapi_dev:view    查看开发者列表与旗下应用
- openapi_dev:status  启用/禁用开发者账号（禁用级联禁用其名下应用）
- openapi_dev:delete  删除开发者账号（级联软删除其名下应用）
开发者账号的注册/资料维护在开放平台门户侧完成，不在此管理。
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_developer_service,
    get_user_operator_context,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.developer import DeveloperResponse, DeveloperStatusRequest
from src.schemas.admin.openapi_app import OpenApiAppResponse
from src.schemas.common import PaginatedResponse
from src.services.admin.developer_admin_service import DeveloperService

router = APIRouter(prefix="/developers", tags=["管理系统：开放平台开发者管理"])


@router.get(
    "",
    summary="开发者用户列表",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_DEV_VIEW.mark))],
)
@permission(PermissionCode.OPENAPI_DEV_VIEW)
def list_developers(
    request: Request,
    keyword: str | None = Query(default=None, description="按用户名/邮箱/姓名模糊搜索"),
    status: str | None = Query(default=None, description="账号状态过滤：enabled/disabled"),
    page: int = Query(default=1, ge=1, description="页码，从 1 起"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    service: DeveloperService = Depends(get_developer_service),
) -> JSONResponse:
    """返回分页的开发者用户列表，含每个用户旗下应用数。

    结构与用户列表等接口一致：{items, total, page, page_size}。
    """
    result = service.list_developers(
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[DeveloperResponse](
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
    "/{developer_id}/apps",
    summary="开发者旗下应用列表",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_DEV_VIEW.mark))],
)
@permission(PermissionCode.OPENAPI_DEV_VIEW)
def list_developer_apps(
    developer_id: int,
    request: Request,
    keyword: str | None = Query(default=None, description="按应用名称模糊搜索"),
    page: int = Query(default=1, ge=1, description="页码，从 1 起"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    service: DeveloperService = Depends(get_developer_service),
) -> JSONResponse:
    """返回指定开发者名下的开放应用分页列表（owner 隔离）。"""
    result = service.list_developer_apps(
        developer_id=developer_id,
        keyword=keyword,
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


@router.post(
    "/{developer_id}/status",
    summary="启用/禁用开发者账号",
    description="禁用开发者账号将级联禁用其名下全部开放应用，并驳回其待审批的申请批次；启用仅恢复账号登录能力。",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_DEV_STATUS.mark))],
)
@permission(PermissionCode.OPENAPI_DEV_STATUS)
def update_developer_status(
    developer_id: int,
    body: DeveloperStatusRequest,
    request: Request,
    service: DeveloperService = Depends(get_developer_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """根据 ID 启用或禁用开发者账号，返回更新后的开发者信息。"""
    result = service.update_status(
        developer_id,
        body.status,
        operator=get_user_operator_context(current_user, request),
    )
    return success_response(result.model_dump(), request)


@router.post(
    "/{developer_id}/delete",
    summary="删除开发者账号",
    description="软删除开发者账号，级联软删除其名下全部开放应用（AppSecret 停止对外服务）；历史审批记录保留。",
    dependencies=[Depends(require_user_permission(PermissionCode.OPENAPI_DEV_DELETE.mark))],
)
@permission(PermissionCode.OPENAPI_DEV_DELETE)
def delete_developer(
    developer_id: int,
    request: Request,
    service: DeveloperService = Depends(get_developer_service),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """根据 ID 软删除开发者账号。"""
    service.delete(developer_id, operator=get_user_operator_context(current_user, request))
    return success_response({"message": "开发者账号删除成功"}, request)
