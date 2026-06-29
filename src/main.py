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
from src.common.constants import APP_NAME, APP_VERSION
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logger import logger, setup_logging
from src.core.middleware import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    在应用启动时初始化日志和核心组件，在应用关闭时执行清理操作。

    Args:
        app: FastAPI 应用实例
    """
    # 启动阶段
    setup_logging()
    logger.info(f"{APP_NAME} v{APP_VERSION} starting up...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.server.SERVER_DEBUG}")
    logger.info(f"Listening on: {settings.server.SERVER_HOST}:{settings.server.SERVER_PORT}")

    # 初始化数据库（仅在配置了数据库连接时）
    if settings.database.DATABASE_URL:
        try:
            from src.core.database import init_db

            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
    else:
        logger.warning("DATABASE_URL not configured, database features disabled")

    yield

    # 关闭阶段
    logger.info(f"{APP_NAME} shutting down...")

    # 关闭数据库连接
    if settings.database.DATABASE_URL:
        try:
            from src.core.database import close_db

            close_db()
            logger.info("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")


def create_app() -> FastAPI:
    """应用工厂函数。

    创建并配置 FastAPI 应用实例，包括：
        1. 注册 CORS 跨域中间件
        2. 注册请求 ID 中间件
        3. 注册全局异常处理器
        4. 挂载 API 路由

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

    # 注册中间件（注意：FastAPI 中间件按添加顺序的逆序执行）
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 挂载 API 路由
    app.include_router(api_router)

    return app


# 创建全局应用实例
app: FastAPI = create_app()


def run() -> None:
    """命令行启动入口。

    使用 uvicorn 运行应用，开发模式下启用热重载。
    生产环境建议使用 Gunicorn + Uvicorn Worker 组合。
    """
    uvicorn.run(
        "src.main:app",
        host=settings.server.SERVER_HOST,
        port=settings.server.SERVER_PORT,
        reload=settings.server.SERVER_DEBUG,
        workers=1 if settings.server.SERVER_DEBUG else settings.server.SERVER_WORKERS,
    )


if __name__ == "__main__":
    run()
