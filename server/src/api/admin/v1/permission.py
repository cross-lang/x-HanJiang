#!/usr/bin/env python3
"""
权限接口（只读）
权限元数据的唯一事实来源是 src.constants.permissions.PermissionCode 目录，
启动同步与种子初始化均从目录派生，故本模块仅提供查询能力，
新增 / 更新 / 删除权限的写接口已移除（页面手工维护会与目录冲突）。

Endpoints:
    GET    /permissions/meta:  权限元数据（模块 / 操作类型去重列表）
    GET    /permissions:       权限列表（分页/过滤）
    GET    /permissions/{id}:  权限详情
"""

from fastapi import APIRouter, Depends, Request

from src.api.admin.permission_decorator import permission
from src.api.admin.dependencies import (
    get_permission_service,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.role import PermissionResponse
from src.schemas.common import PaginatedResponse
from src.services.admin.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["权限管理"])


@router.get(
    "/meta",
    summary="权限元数据",
    description="返回所有去重的模块列表和操作类型列表，供前端下拉选择",
    dependencies=[Depends(require_user_permission(PermissionCode.PERMISSION_VIEW.mark))],
)
@permission(PermissionCode.PERMISSION_VIEW)
def permission_meta(
    request: Request,
    service: PermissionService = Depends(get_permission_service),
):
    """返回模块和操作类型的去重列表。"""
    modules = service.get_all_modules()
    operations = service.get_all_operations()
    return success_response({"modules": modules, "operations": operations}, request)


@router.get(
    "",
    summary="权限列表",
    description="查询权限列表（分页，支持关键字/模块/操作类型过滤）",
    dependencies=[Depends(require_user_permission(PermissionCode.PERMISSION_VIEW.mark))],
)
@permission(PermissionCode.PERMISSION_VIEW)
def list_permissions(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    module: str | None = None,
    operation: str | None = None,
    service: PermissionService = Depends(get_permission_service),
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
            (result["total"] + result["page_size"] - 1) // result["page_size"] if result["page_size"] > 0 else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/{perm_id}",
    summary="权限详情",
    description="根据 ID 查询权限详情",
    dependencies=[Depends(require_user_permission(PermissionCode.PERMISSION_VIEW.mark))],
)
@permission(PermissionCode.PERMISSION_VIEW)
def get_permission(
    perm_id: int,
    request: Request,
    service: PermissionService = Depends(get_permission_service),
):
    """查询单个权限接口。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(perm_id)
    if result is None:
        raise NotFoundException(message=f"权限 {perm_id} 不存在")
    return success_response(result.model_dump(), request)
