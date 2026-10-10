#!/usr/bin/env python3
"""开放平台开发者应用接口（门户 JWT，owner 隔离）。
路由前缀：/api/open-portal/v1/apps（含 GET /apps/scopes scope 目录）

说明：
- 应用数据表 openapi_apps 与管理系统端共用，归属 owner_type='developer' + owner_id=当前开发者；
  开发者只能查询/操作本人名下应用（他人应用一律 404，不暴露存在性）。
- 写操作（创建 / 修改 / scope 调整）统一走申请审批流：向 openapi_app_registrations
  提交申请批次，审批通过后由管理系统落地（见 services/open_portal/app_service.py）。
- 审批记录（GET /{app_id}/approvals）：返回该应用全部申请/审批历史批次，最新在前，
  供门户"审批记录"入口展示多次申请修改权限的完整轨迹。
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
    description="分页查询当前开发者名下的应用（含派生审批状态），仅返回本人数据",
)
def list_apps(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    result = service.list_my_apps(
        current_developer.id,
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
    description="全部可用的开放平台 scope（创建应用/申请权限时展示），按模块分组",
)
def list_scopes(
    request: Request,
    _current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(service.get_public_scopes(), request)


@router.post(
    "",
    summary="提交创建应用申请",
    description="创建应用记录（未授权）+ 生成 create 申请批次，审批通过后应用方可被网关放行",
)
def create_app(
    body: OpenAppCreateRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    data = service.create_app(current_developer.id, payload=body).model_dump()
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
    return success_response(service.get_my_app(app_id, current_developer.id).model_dump(), request)


@router.get(
    "/{app_id}/approvals",
    summary="应用审批记录",
    description="返回该应用全部申请/审批历史批次（创建/修改/scope 调整），最新在前，仅限本人名下应用",
)
def list_approvals(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    records = service.list_approvals(app_id, current_developer.id)
    return success_response([r.model_dump() for r in records], request)


@router.put(
    "/{app_id}",
    summary="提交修改应用申请",
    description="基本信息（name/description/auth_mode）调整走申请审批流，审批通过后快照落地",
)
def update_app(
    app_id: int,
    body: OpenAppUpdateRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(
        service.update_app(app_id, current_developer.id, payload=body).model_dump(),
        request,
    )


@router.put(
    "/{app_id}/scopes",
    summary="提交 scope 申请/调整",
    description="权限范围调整走申请审批流；审批通过后由管理系统将新 scope 落地到应用",
)
def apply_scopes(
    app_id: int,
    body: OpenAppScopeApplyRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    return success_response(
        service.apply_scopes(app_id, current_developer.id, payload=body).model_dump(),
        request,
    )


@router.post(
    "/{app_id}/rotate-key",
    summary="重置 AppKey",
    description="旧 Key 立即失效，新密钥仅本次返回",
)
def rotate_key(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    data = service.rotate_key(app_id, current_developer.id)
    return success_response(OpenAppSecretResponse(**data).model_dump(), request)


@router.post(
    "/{app_id}/view-secret",
    summary="查看 AppKey（一次性）",
    description="创建审批通过后且从未查看过时可查看一次明文 AppKey；查看后该入口关闭，再次获取需重置密钥",
)
def view_secret(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    data = service.view_secret(app_id, current_developer.id)
    return success_response(OpenAppSecretResponse(**data).model_dump(), request)


@router.delete(
    "/{app_id}",
    summary="删除应用",
    description="软删除本人名下应用（不可恢复），其待审批申请一并作废",
)
def delete_app(
    app_id: int,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperOpenApiAppService = Depends(get_developer_openapi_app_service),
) -> JSONResponse:
    service.delete_app(app_id, current_developer.id)
    return success_response({"deleted": True}, request)
