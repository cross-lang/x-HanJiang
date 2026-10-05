#!/usr/bin/env python3
"""
健康检查接口
本模块提供应用健康检查和版本信息查询接口，
用于服务监控、负载均衡健康探测和部署验证。
健康检查发现故障时，由 HealthService 自动触发 system.alert 告警（带节流，避免重复告警）。

Endpoints:
    GET /health: 健康检查（返回数据库、缓存连通状态）
    GET /version: 版本信息
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import get_health_service
from src.api.response import success_response
from src.constants import APP_NAME
from src.core.config import settings
from src.schemas.admin.health import HealthResponse, VersionResponse
from src.services.admin.health_service import HealthService

router = APIRouter(tags=["管理系统：健康检查"])


@router.get(
    "health",
    summary="健康检查",
    description="返回服务健康状态信息，包含数据库、缓存连通状态",
)
def health_check(
    request: Request,
    service: HealthService = Depends(get_health_service),
) -> JSONResponse:
    """健康检查接口。
    下游探测与故障告警统一由 HealthService 完成，本层仅组装响应。
    """
    states = service.check()
    overall_status = "ok" if states["database"] != "error" and states["cache"] != "error" else "error"
    body = HealthResponse(
        status=overall_status,
        app=APP_NAME,
        environment=settings.app_env,
        database=states["database"],
        cache=states["cache"],
    )
    return success_response(body.model_dump(), request)


@router.get(
    "/version",
    summary="版本信息",
    description="返回应用版本号和 API 版本号",
)
async def version(request: Request) -> JSONResponse:
    """版本信息接口。"""
    body = VersionResponse.current()
    return success_response(body.model_dump(), request)
