#!/usr/bin/env python3
"""
应用入口模块

本模块是 FastAPI 应用的核心入口，提供应用工厂函数和启动命令。
负责编排所有组件的初始化顺序：配置加载 → 日志初始化 → 中间件注册 →
异常处理器注册 → 路由挂载 → DI 容器注册。

Functions:
    create_app: 应用工厂函数，创建并配置 FastAPI 实例
    main: 命令行启动入口

Usage:
    # 启动服务
    uv run x-HanJiang

    # 启用热重载（开发模式）
    uv run x-HanJiang --reload

    # 在代码中使用
    from src.main import app
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logger import logger, setup_logging
from src.core.middleware import (
    ExceptionHandlingMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    setup_rate_limiter,
)

try:
    from src.infras.database import get_cached_database_provider
    _has_db = True
except ImportError:
    _has_db = False

try:
    from src.infras.cache import get_cached_cache_provider
    _has_redis = True
except ImportError:
    _has_redis = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    在应用启动时初始化日志和核心组件，在应用关闭时执行清理操作。
    """
    setup_logging()

    logger.info(f"{APP_NAME} v{APP_VERSION} starting up...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.server.debug}")
    logger.info(f"Storage provider: {settings.storage.provider}")
    logger.info(f"Listening on: {settings.server.host}:{settings.server.port}")
    

    if _has_db and settings.database.url:
        try:
            db_provider = get_cached_database_provider()
            from src.infras.database import init_db
            init_db()
            logger.info("Database initialized successfully")
            
            try:
                from src.core.seed import init_seed_data

                init_seed_data()
            except Exception as e:
                logger.warning(f"Seed data initialization skipped: {e}")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
    else:
        logger.info("MySQL connection fields not configured, database features disabled")

    yield

    logger.info(f"{APP_NAME} shutting down...")

    if _has_db and settings.database.url:
        try:
            get_cached_database_provider().close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

    if _has_redis and settings.redis.url:
        try:
            get_cached_cache_provider().close()
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
        5. 配置慢 API 限流器
        6. 注册默认 DI 绑定
        7. 挂载 API 路由

    Returns:
        FastAPI: 配置完成的 FastAPI 应用实例
    """
    app: FastAPI = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 中间件顺序：后注册的在外层（最后处理请求，最先处理响应）
    # ExceptionHandlingMiddleware 最先注册，最后执行 → 兜底
    app.add_middleware(ExceptionHandlingMiddleware)
    # RequestLoggingMiddleware 次之
    app.add_middleware(RequestLoggingMiddleware)
    # RequestIDMiddleware 最先执行
    app.add_middleware(RequestIDMiddleware)

    # CORS 必须在最后注册 → 最外层，处理 OPTIONS 预检
    # 修复 #8: allow_credentials=True 时不允许 "*"
    cors_origins = settings.cors.origins
    if "*" in cors_origins and settings.is_production:
        logger.warning(
            "CORS origins 含 '*' 且生产环境启用凭据转发，浏览器会拒绝；"
            "请在配置中指定可信来源列表"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials="*" not in cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # 限流器注册（在应用 state 上挂载 limiter，slowapi 通过装饰器使用）
    try:
        setup_rate_limiter(app)
        logger.info(
            f"Rate limiter enabled: {settings.rate_limit.per_minute} req/min per IP"
        )
    except Exception as e:
        logger.warning(f"Rate limiter setup failed (slowapi not installed?): {e}")

    app.include_router(api_router)

    return app


app: FastAPI = create_app()


def main() -> None:
    """命令行启动入口（pyproject.toml 中的 entry point）。

    支持通过 CLI 参数控制启动行为：
        uv run x-HanJiang                # 默认启动
        uv run x-HanJiang --reload        # 热重载（开发模式）
        uv run x-HanJiang --port 9000     # 自定义端口
        uv run x-HanJiang -V              # 查看版本
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="x-HanJiang",
        description="汉江（HanJiang） — 基于 FastAPI 的生产级 Web 应用框架",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"x-HanJiang {APP_VERSION}",
    )
    parser.add_argument(
        "--host",
        default=settings.server.host,
        help=f"服务器监听地址（默认 {settings.server.host}）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.server.port,
        help=f"服务器监听端口（默认 {settings.server.port}）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（开发模式）",
    )
    args = parser.parse_args()

    reload = args.reload or settings.server.debug
    workers = 1 if reload else settings.server.workers

    logger.info(f"Starting {APP_NAME} v{APP_VERSION}...")
    logger.info(f"  Address:  http://{args.host}:{args.port}")
    logger.info(f"  Reload:   {reload}")
    logger.info(f"  Workers:  {workers}")

    uvicorn.run(
        "src.main:app",
        host=args.host,
        port=args.port,
        reload=reload,
        workers=workers,
    )


if __name__ == "__main__":
    main()
