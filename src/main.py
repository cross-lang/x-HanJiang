#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用入口模块

本模块是 FastAPI 应用的核心入口，提供应用工厂函数和启动命令。
负责编排所有组件的初始化顺序：配置加载 → 日志初始化 → 中间件注册 →
异常处理器注册 → 路由挂载。

Functions:
    create_app: 应用工厂函数，创建并配置 FastAPI 实例
    run: 命令行启动入口

Usage:
    # 开发模式启动
    uv run python -m src.main

    # 或使用 uvicorn
    uv run uvicorn src.main:app --reload

    # 在代码中使用
    from src.main import app
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.constants import APP_NAME, APP_VERSION
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logger import logger, setup_logging
from src.core.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)

try:
    from src.infra.database import init_db, close_db
    _has_db = True
except ImportError:
    _has_db = False

try:
    from src.infra.cache import close_redis
    _has_redis = True
except ImportError:
    _has_redis = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    在应用启动时初始化日志和核心组件，在应用关闭时执行清理操作。

    Args:
        app: FastAPI 应用实例
    """
    setup_logging()
    logger.info(f"{APP_NAME} v{APP_VERSION} starting up...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.server.debug}")
    logger.info(f"Listening on: {settings.server.host}:{settings.server.port}")

    if _has_db and settings.database.url:
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
    else:
        logger.warning("DATABASE_URL not configured, database features disabled")

    yield

    logger.info(f"{APP_NAME} shutting down...")

    if _has_db and settings.database.url:
        try:
            close_db()
            logger.info("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

    if _has_redis and settings.redis.url:
        try:
            close_redis()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")


def create_app() -> FastAPI:
    """应用工厂函数。

    创建并配置 FastAPI 应用实例，包括：
        1. 注册 CORS 跨域中间件
        2. 注册请求 ID 中间件
        3. 注册请求日志记录中间件
        4. 注册全局异常处理器
        5. 挂载 API 路由

    Returns:
        FastAPI: 配置完成的 FastAPI 应用实例
    """
    app: FastAPI = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="A production-grade FastAPI project template",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(api_router)

    return app


app: FastAPI = create_app()


def run() -> None:
    """命令行启动入口。

    使用 uvicorn 运行应用，开发模式下启用热重载。
    生产环境建议使用 Gunicorn + Uvicorn Worker 组合。
    """
    uvicorn.run(
        "src.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug,
        workers=1 if settings.server.debug else settings.server.workers,
    )


if __name__ == "__main__":
    run()