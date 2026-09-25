#!/usr/bin/env python3
"""开放平台健康检查与版本信息接口。

- GET /health：公开探活，给负载均衡/监控用，不暴露内部依赖状态；
- GET /version：公开，返回开放平台 API 版本号。

这两个接口不要求 AppId/AppKey 鉴权——监控系统和调用方联调时需要先确认服务活着，
再去带凭证调业务接口。带鉴权的连通性验证走 /api/open/v1/ping。
"""

from fastapi import APIRouter, Request

from src.api.response import success_response
from src.constants import APP_NAME, APP_VERSION

router = APIRouter(tags=["开放平台：健康管理"])


@router.get("/health", summary="开放平台健康检查")
async def openapi_health(request: Request):
    """轻量探活，返回开放平台网关状态。

    不检查数据库/Redis——内部依赖健康度由用户态 /api/v1/health 负责，
    外部调用方无需感知内部拓扑。
    """
    return success_response(
        {
            "status": "ok",
            "service": "openapi",
            "app": APP_NAME,
        },
        request,
    )


@router.get("/version", summary="开放平台版本信息")
async def openapi_version(request: Request):
    """返回开放平台 API 版本号。"""
    return success_response(
        {
            "app_version": APP_VERSION,
            "api_version": "v1",
        },
        request,
    )
