#!/usr/bin/env python3
"""开放 API 角色管理接口。
将角色管理核心能力暴露给外部服务，通过 AppId/AppKey + scope 鉴权。
operator 上下文记录为调用方应用，而非终端用户。

能力面：角色 CRUD + 角色权限查询（role:read / role:write）。
角色权限的绑定/解绑属管理端管理行为（需用户态 ROLE_PERMISSION 权限体系），
不对外部应用开放，避免第三方集成方改动权限体系。
"""


from typing import Any

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import get_role_service
from src.api.open.dependencies import (
    get_app_operator_context,
    get_current_app,
    require_app_scope,
)
from src.api.open.scope_decorator import app_scope
from src.api.response import success_response
from src.constants.scopes import OpenApiScopeCode
from src.schemas.common import ApiResponse, PaginatedResponse
from src.schemas.open.app import CurrentApp
from src.schemas.role import (
    PermissionResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from src.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["开放API：角色管理"])


@router.get(
    "",
    summary="开放 API 角色列表",
    response_model=ApiResponse[PaginatedResponse[RoleResponse]],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ROLE_READ.mark))],
)
@app_scope(OpenApiScopeCode.ROLE_READ)
def list_roles(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页记录数"),
    keyword: str | None = Query(default=None, description="关键字（角色名称/编码）"),
    role_type: str | None = Query(default=None, description="角色类型过滤（system/custom）"),
    status: str | None = Query(default=None, description="状态过滤（enabled/disabled）"),
    app: CurrentApp = Depends(get_current_app),
    service: RoleService = Depends(get_role_service),
) -> JSONResponse:
    """查询角色列表（需 `role:read` scope）。"""
    result = service.search(keyword=keyword, role_type=role_type, status=status, page=page, page_size=page_size)
    page_result = PaginatedResponse[RoleResponse](
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
    "",
    summary="开放 API 创建角色",
    response_model=ApiResponse[RoleResponse],
    status_code=201,
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ROLE_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.ROLE_WRITE)
def create_role(
    body: RoleCreateRequest,
    request: Request,
    app: CurrentApp = Depends(get_current_app),
    service: RoleService = Depends(get_role_service),
) -> JSONResponse:
    """创建角色（需 `role:write` scope）。"""
    result = service.create(body.model_dump(), operator=get_app_operator_context(app))
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "/{role_id}",
    summary="开放 API 角色详情",
    response_model=ApiResponse[RoleResponse],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ROLE_READ.mark))],
)
@app_scope(OpenApiScopeCode.ROLE_READ)
def get_role(
    request: Request,
    role_id: int = Path(ge=1, description="角色 ID"),
    app: CurrentApp = Depends(get_current_app),
    service: RoleService = Depends(get_role_service),
) -> JSONResponse:
    """查询单个角色详情（需 `role:read` scope）。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(role_id)
    if result is None:
        raise NotFoundException(message=f"角色 {role_id} 不存在")
    return success_response(result.model_dump(), request)


@router.patch(
    "/{role_id}",
    summary="开放 API 更新角色",
    response_model=ApiResponse[RoleResponse],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ROLE_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.ROLE_WRITE)
def update_role(
    body: RoleUpdateRequest,
    request: Request,
    role_id: int = Path(ge=1, description="角色 ID"),
    app: CurrentApp = Depends(get_current_app),
    service: RoleService = Depends(get_role_service),
) -> JSONResponse:
    """更新角色信息（需 `role:write` scope）。"""
    result = service.update(role_id, body.model_dump(exclude_unset=True), operator=get_app_operator_context(app))
    return success_response(result.model_dump(), request)


@router.delete(
    "/{role_id}",
    summary="开放 API 删除角色",
    response_model=ApiResponse[dict[str, Any]],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ROLE_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.ROLE_WRITE)
def delete_role(
    request: Request,
    role_id: int = Path(ge=1, description="角色 ID"),
    app: CurrentApp = Depends(get_current_app),
    service: RoleService = Depends(get_role_service),
) -> JSONResponse:
    """软删除角色（需 `role:write` scope；有关联用户的角色不可删除）。"""
    service.delete(role_id, operator=get_app_operator_context(app))
    return success_response({"deleted": True}, request)


@router.get(
    "/{role_id}/permissions",
    summary="开放 API 角色权限列表",
    response_model=ApiResponse[list[PermissionResponse]],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ROLE_READ.mark))],
)
@app_scope(OpenApiScopeCode.ROLE_READ)
def get_role_permissions(
    request: Request,
    role_id: int = Path(ge=1, description="角色 ID"),
    app: CurrentApp = Depends(get_current_app),
    service: RoleService = Depends(get_role_service),
) -> JSONResponse:
    """查询角色绑定的权限列表（需 `role:read` scope）。"""
    result = service.get_permissions(role_id)
    return success_response([r.model_dump() for r in result], request)
