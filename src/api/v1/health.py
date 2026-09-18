#!/usr/bin/env python3
"""
健康检查接口

本模块提供应用健康检查和版本信息查询接口，
用于服务监控、负载均衡健康探测和部署验证。

Endpoints:
    GET /health: 健康检查（返回数据库、缓存连通状态）
    GET /version: 版本信息
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.response import success_response
from src.constants import APP_NAME
from src.core.config import settings
from src.schemas.health import HealthResponse, VersionResponse

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    summary="健康检查",
    description="返回服务健康状态信息，包含数据库、缓存连通状态",
)
async def health_check(request: Request) -> JSONResponse:
    """健康检查接口。

    返回服务当前运行状态、版本号、环境信息，以及数据库和缓存的连通状态。
    """
    database_status = _check_database()
    cache_status = _check_cache()

    overall_status = "ok"
    if database_status == "error" or cache_status == "error":
        overall_status = "error"

    body = HealthResponse(
        status=overall_status,
        app=APP_NAME,
        version=settings.app_env and "",  # 占位，下行覆盖
        environment=settings.app_env,
        database=database_status,
        cache=cache_status,
    )
    # 注入应用版本
    from src.constants import APP_VERSION
    body = body.model_copy(update={"version": APP_VERSION})
    return success_response(body.model_dump(), request)


def _check_database() -> str:
    """检查数据库连接状态。"""
    if not settings.database.url:
        return "disabled"

    try:
        from sqlalchemy import text

        from src.infras.database import get_cached_database_provider

        engine = get_cached_database_provider().get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        from src.core.logger import logger

        logger.warning(f"Database connection check failed: {e}")
        return "error"


def _check_cache() -> str:
    """检查缓存连接状态。"""
    if not settings.redis.url:
        return "disabled"

    try:
        from src.infras.cache import get_cached_cache_provider

        provider = get_cached_cache_provider()
        provider.ping()
        return "ok"
    except ImportError:
        return "disabled"
    except Exception as e:
        from src.core.logger import logger

        logger.warning(f"Redis connection check failed: {e}")
        return "error"


@router.get(
    "/version",
    summary="版本信息",
    description="返回应用版本号和 API 版本号",
)
async def version(request: Request) -> JSONResponse:
    """版本信息接口。"""
    body = VersionResponse.current()
    return success_response(body.model_dump(), request)
