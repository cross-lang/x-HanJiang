#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查接口

本模块提供应用健康检查和版本信息查询接口，
用于服务监控、负载均衡健康探测和部署验证。

Endpoints:
    GET /health: 健康检查（返回数据库、缓存连通状态）
    GET /version: 版本信息
"""

from fastapi import APIRouter, Request

from src.constants import APP_NAME, APP_VERSION
from src.core.config import settings
from src.schemas.health import HealthResponse, VersionResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="健康检查",
    description="返回服务健康状态信息，包含数据库、缓存连通状态",
    response_model=HealthResponse,
)
async def health_check(request: Request) -> HealthResponse:
    """健康检查接口。

    返回服务当前运行状态、版本号、环境信息，以及数据库和缓存的连通状态。
    用于负载均衡器健康探测和监控系统。

    Args:
        request: FastAPI 请求对象

    Returns:
        HealthResponse: 健康检查响应模型
    """
    database_status = _check_database()
    cache_status = _check_cache()

    overall_status = "ok"
    if database_status == "error" or cache_status == "error":
        overall_status = "error"

    return HealthResponse(
        status=overall_status,
        app=APP_NAME,
        version=APP_VERSION,
        environment=settings.app_env,
        database=database_status,
        cache=cache_status,
    )


def _check_database() -> str:
    """检查数据库连接状态。

    Returns:
        str: "ok" 表示连接正常，"error" 表示连接失败，"disabled" 表示未配置
    """
    if not settings.database.url:
        return "disabled"

    try:
        from src.infra.mysql import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        from src.core.logger import logger

        logger.warning(f"Database connection check failed: {e}")
        return "error"


def _check_cache() -> str:
    """检查缓存连接状态。

    Returns:
        str: "ok" 表示连接正常，"error" 表示连接失败，"disabled" 表示未配置
    """
    if not settings.redis.url:
        return "disabled"

    try:
        from src.infra.cache import get_redis

        redis_client = get_redis()
        redis_client.ping()
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
    response_model=VersionResponse,
)
async def version(request: Request) -> VersionResponse:
    """版本信息接口。

    返回应用版本号和 API 版本号。

    Args:
        request: FastAPI 请求对象

    Returns:
        VersionResponse: 版本信息响应模型
    """
    return VersionResponse(
        version=APP_VERSION,
        api_version="v1",
    )