#!/usr/bin/env python3
"""开放平台开发者应用接口（门户 JWT，owner 隔离）。
路由前缀：/api/open-portal/v1/apps（含 GET /apps/scopes scope 目录）
说明：应用数据表 openapi_apps 与管理系统端共用，归属 owner_type='developer' + owner_id=当前开发者；
开发者只能查询/操作本人名下应用（他人应用一律 404，不暴露存在性）。
scope 目录接口（GET /apps/scopes）的元数据唯一来源为 openapi_scopes 表（constants/scopes.py 启动时对账），
与管理端 /api/v1/apps/scopes 路径风格一致，业务实现下放 DeveloperOpenApiAppService.list_scopes。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.open_portal.dependencies import (
    get_current_developer,
    get_developer_openapi_app_service,
)
from src.api.response import success_response
from src.schemas.common import PaginatedResponse
from src.schemas.open_portal.app import (
    OpenAppCreatedResponse,
    OpenAppCreateRequest,
    OpenAppResponse,
    OpenAppScopeApplyRequest,
    OpenAppSecretResponse,
    OpenAppUpdateRequest,
)
from src.schemas.open_portal.auth import CurrentDeveloper
from src.services.open_portal.app_service import DeveloperOpenApiAppService

router = APIRouter(prefix="/apps", tags=["开放平台：开发者应用"])

@router.get(
    "",
    summary="我的应用列表",
    description="分页查询当前开发者名下的应用（含审批状态），仅返回本人数据",
)
def list_apps(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    result = service.list_apps(
        developer_id=current_developer.id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[OpenAppResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"] if result["page_size"] > 0 else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


# 注意：GET /scopes 必须声明在 GET /{app_id} 之前——FastAPI 按注册顺序匹配，
# 若放在 /{app_id} 之后，/apps/scopes 会被其抢先捕获导致 app_id="scopes" 解析失败（422）。
@router.get(
    "/scopes",
    summary="scope 目录",
    description="全部可用（未废弃）的开放平台 scope，按模块分组展示",
)
def list_scopes(
    request: Request,
    _current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(service.list_scopes(), request)


@router.post(
    "",
    summary="创建应用（含 scope 申请）",
    description="创建即申请：scope 落到应用上，审批状态为 pending，等待管理员审批；AppKey 明文仅本次返回",
)
def create_app(
    body: OpenAppCreateRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    resp, app_key = service.create_app(
        developer_id=current_developer.id,
        name=body.name,
        description=body.description,
        scopes=body.scopes,
        auth_mode=body.auth_mode,
    )
    data = OpenAppCreatedResponse(**resp.model_dump(), app_key=app_key).model_dump()
    return success_response(data, request, code=201)


@router.get(
    "/{app_id}",
    summary="应用详情",
    description="仅返回本人名下应用",
)
def get_app(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(service.get_app(app_id, current_developer.id).model_dump(), request)


@router.put(
    "/{app_id}",
    summary="更新应用",
    description="更新应用基本信息（name/description/auth_mode），scope 调整走独立申请端点",
)
def update_app(
    app_id: int,
    body: OpenAppUpdateRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(
        service.update_app(
            app_id,
            current_developer.id,
            body.model_dump(exclude_unset=True),
        ).model_dump(),
        request,
    )


@router.put(
    "/{app_id}/scopes",
    summary="提交 scope 申请/调整",
    description="更新目标 scopes 并置审批状态为 pending，等待管理员审批；取消勾选表示申请收回权限",
)
def apply_scopes(
    app_id: int,
    body: OpenAppScopeApplyRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(
        service.apply_scopes(
            app_id,
            current_developer.id,
            body.scopes,
            body.reason,
        ).model_dump(),
        request,
    )


@router.post(
    "/{app_id}/rotate-key",
    summary="重置 AppKey",
    description="旧 Key 立即失效，新明文仅本次返回",
)
def rotate_key(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    resp, new_key = service.rotate_key(app_id, current_developer.id)
    data = OpenAppSecretResponse(app_id=resp.app_id, app_key=new_key).model_dump()
    return success_response(data, request)


@router.delete(
    "/{app_id}",
    summary="删除应用",
    description="软删除本人名下应用（不可恢复）",
)
def delete_app(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    ok = service.delete_app(app_id, current_developer.id)
    return success_response({"deleted": ok}, request)
