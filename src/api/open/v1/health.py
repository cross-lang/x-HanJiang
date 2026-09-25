#!/usr/bin/env python3
"""开放平台健康管理接口。

"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import CurrentApp, get_current_app, require_app_scope
from src.api.response import success_response
from src.constants import APP_NAME, APP_VERSION

router = APIRouter(tags=["开放平台：健康管理"])


@router.get("/health", summary="开放平台健康检查")
async def openapi_health(
    request: Request,
    app: CurrentApp = Depends(get_current_app),
):
    """轻量探活，确认开放平台网关正常且调用方凭证有效。"""
    return success_response(
        {
            "status": "ok",
            "service": "openapi",
            "app": APP_NAME,
        },
        request,
    )


@router.get("/version", summary="开放平台版本信息")
async def openapi_version(
    request: Request,
    app: CurrentApp = Depends(get_current_app),
):
    """返回开放平台 API 版本号。"""
    return success_response(
        {
            "app_version": APP_VERSION,
            "api_version": "v1",
        },
        request,
    )


@router.get("/ping", summary="连通性测试")
async def ping(
    request: Request,
    app: CurrentApp = Depends(require_app_scope("ping:read")),
):
    """返回当前调用方应用身份，用于联调验证。需 `ping:read` scope。"""
    return success_response(
        {
            "message": "pong",
            "app_id": app.app_id,
            "app_name": app.name,
            "scopes": app.scopes,
            "auth_mode": app.auth_mode,
        },
        request,
    )
