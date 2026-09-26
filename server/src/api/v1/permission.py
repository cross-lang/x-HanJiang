#!/usr/bin/env python3
"""
权限接口

提供权限管理的 RESTful API 端点（CRUD）。

Endpoints:
    GET    /permissions:      权限列表（分页/过滤）
    POST   /permissions:      创建权限
    GET    /permissions/{id}: 权限详情
    POST   /permissions/{id}/update: 更新权限
    POST   /permissions/{id}/delete: 删除权限
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import (
    get_current_user,
    get_permission_service,
    get_user_operator_context,
    require_user_permission,
)
from src.api.response import success_response
from src.schemas.auth import CurrentUser
from src.schemas.common import PaginatedResponse
from src.schemas.role import PermissionResponse
from src.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["权限管理"])


@router.get(
    "",
    summary="权限列表",
    description="查询权限列表（分页，支持关键字/模块/操作类型过滤）",
)
async def list_permissions(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    module: str | None = None,
    operation: str | None = None,
    service: PermissionService = Depends(get_permission_service),
    _=Depends(require_user_permission("role:view")),
):
    """权限列表接口。"""
    result = service.search(
        keyword=keyword,
        module=module,
        operation=operation,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[PermissionResponse](
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


@router.post(
    "",
    summary="创建权限",
    description="创建一个新权限（校验编码唯一）",
    status_code=201,
)
async def create_permission(
    body: dict,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: CurrentUser = Depends(get_current_user),
    _=Depends(require_user_permission("role:edit")),
):
    """创建权限接口。"""
    result = service.create(body, operator=get_user_operator_context(current_user))
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "/{perm_id}",
    summary="权限详情",
    description="根据 ID 查询权限详情",
)
async def get_permission(
    perm_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    _=Depends(require_user_permission("role:view")),
):
    """查询单个权限接口。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(perm_id)
    if result is None:
        raise NotFoundException(message=f"权限 {perm_id} 不存在")
    return success_response(result.model_dump(), request)


@router.post(
    "/{perm_id}/update",
    summary="更新权限",
    description="更新权限信息",
)
async def update_permission(
    perm_id: int,
    body: dict,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: CurrentUser = Depends(get_current_user),
    _=Depends(require_user_permission("role:edit")),
):
    """更新权限接口。"""
    result = service.update(
        perm_id,
        body,
        operator=get_user_operator_context(current_user),
    )
    return success_response(result.model_dump(), request)


@router.post(
    "/{perm_id}/delete",
    summary="删除权限",
    description="根据 ID 删除权限",
)
async def delete_permission(
    perm_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: CurrentUser = Depends(get_current_user),
    _=Depends(require_user_permission("role:delete")),
):
    """删除权限接口。"""
    service.delete(perm_id, operator=get_user_operator_context(current_user))
    return success_response({"message": "权限删除成功"}, request)
