#!/usr/bin/env python3
"""开放 API 健康管理接口。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.open.dependencies import get_current_app
from src.api.response import success_response
from src.constants import APP_NAME, APP_VERSION
from src.schemas.common import ApiResponse
from src.schemas.open.health import HealthResponse, VersionResponse

router = APIRouter(tags=["开放API：健康管理"])


@router.get(
    "/health",
    summary="开放 API 健康检查",
    response_model=ApiResponse[HealthResponse],
    dependencies=[Depends(get_current_app)],
)
async def openapi_health(
    request: Request,
) -> JSONResponse:
    """轻量探活，确认开放 API 网关正常且调用方凭证有效。"""
    return success_response(
        {
            "status": "ok",
            "service": "openapi",
            "app": APP_NAME,
        },
        request,
    )


@router.get(
    "/version",
    summary="开放 API 版本信息",
    response_model=ApiResponse[VersionResponse],
    dependencies=[Depends(get_current_app)],
)
async def openapi_version(
    request: Request,
) -> JSONResponse:
    """返回开放 API 版本号。"""
    return success_response(
        {
            "app_version": APP_VERSION,
            "api_version": "v1",
        },
        request,
    )

