#!/usr/bin/env python3
"""
健康检查接口

本模块提供应用健康检查和版本信息查询接口，
用于服务监控、负载均衡健康探测和部署验证。
健康检查发现故障时，自动触发 system.alert 告警（带节流，避免重复告警）。

Endpoints:
    GET /health: 健康检查（返回数据库、缓存连通状态）
    GET /version: 版本信息
"""

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.response import success_response
from src.constants import APP_NAME
from src.core.config import settings
from src.core.logger import logger
from src.schemas.health import HealthResponse, VersionResponse

router = APIRouter(tags=["健康检查"])

# 告警节流：{ component: last_alert_timestamp }
_alert_throttle: dict[str, float] = {}
_ALERT_COOLDOWN_SECONDS = 300  # 同一组件 5 分钟内不重复告警


@router.get(
    "/health",
    summary="健康检查",
    description="返回服务健康状态信息，包含数据库、缓存连通状态",
)
async def health_check(request: Request) -> JSONResponse:
    """健康检查接口。

    返回服务当前运行状态、版本号、环境信息，以及数据库和缓存的连通状态。
    当检测到故障时，自动触发告警通知（带节流）。
    """
    database_status = _check_database()
    cache_status = _check_cache()

    overall_status = "ok"
    if database_status == "error" or cache_status == "error":
        overall_status = "error"

    # ── 故障时自动触发告警 ──
    if database_status == "error":
        _trigger_alert("database", "数据库连接异常")
    if cache_status == "error":
        _trigger_alert("cache", "Redis 缓存连接异常")

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


def _trigger_alert(component: str, message: str) -> None:
    """触发告警（带节流，同一组件 5 分钟内不重复发送）。"""
    now = time.time()
    last_alert = _alert_throttle.get(component, 0)
    if now - last_alert < _ALERT_COOLDOWN_SECONDS:
        return
    _alert_throttle[component] = now

    try:
        from src.infras.notification import get_registry
        from src.notification.dispatcher import NotificationDispatcher
        from src.services.alert_service import AlertService

        alert_email = settings.notification.alert_email
        if not alert_email:
            logger.warning("Health check alert skipped: notification.alert_email not configured")
            return

        dispatcher = NotificationDispatcher(registry=get_registry(), session=None)
        service = AlertService(dispatcher=dispatcher, session=None)
        service.send(
            subject=f"[健康检查] {component} 故障",
            message=f"健康检查检测到 {message}，请立即排查。",
            recipients={"email": alert_email},
        )
    except Exception as e:
        logger.warning(f"Health check alert trigger failed: {e}")


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
