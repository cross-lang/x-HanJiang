#!/usr/bin/env python3
"""开放平台应用管理接口（内部管理员用，走用户态 JWT）。
路由前缀：/api/v1/admin/apps
权限：SUPERADMIN
注意：AppKey 明文只在创建 / 重置时返回一次，之后无法再查看。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.api_permission_decorator import permission
from src.api.dependencies import get_current_user, get_openapi_app_service, require_user_permission
from src.api.response import success_response
from src.schemas.openapi_app import (
    OpenApiAppCreatedResponse,
    OpenApiAppCreateRequest,
    OpenApiAppScopesUpdateRequest,
    OpenApiAppUpdateRequest,
)
from src.services.openapi_app_service import OpenApiAppService

router = APIRouter(prefix="/admin/apps", tags=["开放平台应用管理"])


@router.get("/scopes", summary="可用 scope 列表", dependencies=[Depends(require_user_permission("openapi_scope:view"))])
@permission("openapi_scope:view", "查看开放应用权限", "openapi_scope", "view")
def list_scopes(
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
) -> JSONResponse:
    """返回所有可用的开放平台 scope（分组展示给前端创建应用时勾选）。"""
    return success_response(service.list_scopes(), request)


@router.post("", summary="创建开放应用", dependencies=[Depends(require_user_permission("openapi_app:create"))])
@permission("openapi_app:create", "创建开放应用", "openapi_app", "create")
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
        scopes=body.scopes,
        rate_limit_per_minute=body.rate_limit_per_minute,
        auth_mode=body.auth_mode,
        owner_user_id=current_user.id,
    )
    data = OpenApiAppCreatedResponse(**resp.model_dump(), app_key=app_key).model_dump()
    return success_response(data, request)


@router.get("", summary="应用列表", dependencies=[Depends(require_user_permission("openapi_app:view"))])
@permission("openapi_app:view", "查看开放应用", "openapi_app", "view")
def list_apps(
    request: Request,
    keyword: str | None = None,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    items = service.list_apps(keyword=keyword)
    return success_response([i.model_dump() for i in items], request)


@router.get("/{app_id}", summary="应用详情", dependencies=[Depends(require_user_permission("openapi_app:view"))])
@permission("openapi_app:view", "查看开放应用", "openapi_app", "view")
def get_app(
    app_id: int,
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    return success_response(service.get_by_id(app_id).model_dump(), request)


@router.put("/{app_id}", summary="更新应用", dependencies=[Depends(require_user_permission("openapi_app:edit"))])
@permission("openapi_app:edit", "编辑开放应用", "openapi_app", "edit")
def update_app(
    app_id: int,
    body: OpenApiAppUpdateRequest,
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    return success_response(
        service.update(app_id, body.model_dump(exclude_unset=True)).model_dump(),
        request,
    )


@router.put(
    "/{app_id}/scopes", summary="更新应用 scope", dependencies=[Depends(require_user_permission("openapi_app:edit"))]
)
@permission("openapi_app:edit", "编辑开放应用", "openapi_app", "edit")
def update_app_scopes(
    app_id: int,
    body: OpenApiAppScopesUpdateRequest,
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    """覆盖更新应用的 scope 列表。传入的 scopes 会完全覆盖原有值。"""
    return success_response(
        service.update(app_id, {"scopes": body.scopes}).model_dump(),
        request,
    )


@router.post(
    "/{app_id}/rotate-key", summary="重置 AppKey", dependencies=[Depends(require_user_permission("openapi_app:edit"))]
)
@permission("openapi_app:edit", "编辑开放应用", "openapi_app", "edit")
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


@router.delete("/{app_id}", summary="删除应用", dependencies=[Depends(require_user_permission("openapi_app:delete"))])
@permission("openapi_app:delete", "删除开放应用", "openapi_app", "delete")
def delete_app(
    app_id: int,
    request: Request,
    service: OpenApiAppService = Depends(get_openapi_app_service),
):
    ok = service.delete(app_id)
    return success_response({"deleted": ok}, request)
