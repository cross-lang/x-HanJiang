#!/usr/bin/env python3
"""
角色接口

提供角色管理与角色权限查询的 RESTful API 端点。

Endpoints:
    GET    /roles:                             角色列表（分页/过滤）
    POST   /roles:                             创建角色
    GET    /roles/{id}:                        角色详情
    POST   /roles/{id}/update:                 更新角色
    POST   /roles/{id}/delete:                 删除角色（软删除）
    GET    /roles/{id}/permissions:            角色权限列表（含权限详情）
    POST   /roles/{id}/permissions:            为角色绑定权限
    POST   /roles/{id}/permissions/{pid}/unbind: 解除角色权限绑定
"""

from fastapi import APIRouter, Depends, Request

from src.api.permission_decorator import permission
from src.api.dependencies import (
    get_current_user,
    get_user_operator_context,
    get_permission_service,
    get_role_service,
    require_user_permission,
)
from src.api.response import success_response
from src.schemas.auth import CurrentUser
from src.schemas.common import PaginatedResponse
from src.schemas.role import (
    BindPermissionRequest,
    PermissionResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from src.services.permission_service import PermissionService
from src.services.role_service import RoleService
from src.constants.enums import PermissionCode

router = APIRouter(prefix="/roles", tags=["角色管理"])


@router.get(
    "",
    summary="角色列表",
    description="查询角色列表（分页，支持关键字/类型/状态过滤）",
)
@permission("role:view", "查看角色", "role", "view")
async def list_roles(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    role_type: str | None = None,
    status: str | None = None,
    service: RoleService = Depends(get_role_service),
):
    """角色列表接口。"""
    result = service.search(
        keyword=keyword,
        role_type=role_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[RoleResponse](
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
    summary="创建角色",
    description="创建一个新角色（校验编码/名称唯一）",
    status_code=201,
)
@permission("role:create", "创建角色", "role", "create")
async def create_role(
    body: RoleCreateRequest,
    request: Request,
    service: RoleService = Depends(get_role_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    """创建角色接口。"""
    result = service.create(body.model_dump(), operator=get_user_operator_context(current_user))
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "/{role_id}",
    summary="角色详情",
    description="根据 ID 查询角色详情",
)
@permission("role:view", "查看角色", "role", "view")
async def get_role(
    role_id: int,
    request: Request,
    service: RoleService = Depends(get_role_service),
):
    """查询单个角色接口。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(role_id)
    if result is None:
        raise NotFoundException(message=f"角色 {role_id} 不存在")
    return success_response(result.model_dump(), request)


@router.post(
    "/{role_id}/update",
    summary="更新角色",
    description="更新角色信息（名称/描述/状态）",
)
@permission("role:edit", "编辑角色", "role", "edit")
async def update_role(
    role_id: int,
    body: RoleUpdateRequest,
    request: Request,
    service: RoleService = Depends(get_role_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新角色接口。"""
    result = service.update(
        role_id,
        body.model_dump(exclude_unset=True),
        operator=get_user_operator_context(current_user),
    )
    return success_response(result.model_dump(), request)


@router.post(
    "/{role_id}/delete",
    summary="删除角色",
    description="根据 ID 软删除角色",
)
@permission("role:delete", "删除角色", "role", "delete")
async def delete_role(
    role_id: int,
    request: Request,
    service: RoleService = Depends(get_role_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除角色接口。"""
    service.delete(role_id, operator=get_user_operator_context(current_user))
    return success_response({"message": "角色删除成功"}, request)


@router.get(
    "/{role_id}/permissions",
    summary="角色权限列表",
    description="查询角色绑定的权限列表（含权限详情）",
)
@permission("role:view", "查看角色", "role", "view")
async def get_role_permissions(
    role_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
):
    """查询角色权限列表接口。"""
    result = service.get_role_permissions(role_id)
    return success_response([r.model_dump() for r in result], request)


@router.post(
    "/{role_id}/permissions",
    summary="绑定权限",
    description="为角色绑定一个权限",
    status_code=201,
)
@permission("role:edit", "编辑角色", "role", "edit")
async def bind_permission(
    role_id: int,
    body: BindPermissionRequest,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    """为角色绑定权限接口。"""
    result = service.bind_permission(
        role_id,
        body.permission_id,
        operator=get_user_operator_context(current_user),
    )
    return success_response(result.model_dump(), request, code=201)


@router.post(
    "/{role_id}/permissions/{permission_id}/unbind",
    summary="解绑权限",
    description="解除角色与指定权限的绑定",
)
@permission("role:edit", "编辑角色", "role", "edit")
async def unbind_permission(
    role_id: int,
    permission_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    """解除角色权限绑定接口。"""
    service.unbind_permission(
        role_id,
        permission_id,
        operator=get_user_operator_context(current_user),
    )
    return success_response({"message": "权限解绑成功"}, request)
