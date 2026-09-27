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

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router, open_router
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
from src.infras.cache import get_cached_cache_provider
from src.infras.database import get_cached_database_provider

try:
    from slowapi import Limiter  # noqa: F401
    _has_slowapi = True
except ImportError:
    _has_slowapi = False



@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    setup_logging()

    logger.info(f"{APP_NAME} v{APP_VERSION} starting up (env={settings.app_env}, debug={settings.server.debug})")

    # 初始化数据库
    get_cached_database_provider()
    from src.infras.database import init_db
    init_db()
    logger.info("Database initialized successfully")

    # 初始化种子数据
    from src.core.seed import init_seed_data
    init_seed_data()

    # 自动扫描路由中的权限声明，同步到 permissions 表
    try:
        from src.api.permission_decorator import collect_permissions_from_app
        from src.models.entities.user_entity import PermissionEntity

        collected = collect_permissions_from_app(app)
        logger.debug(f"Collected permissions: {[p['perm_code'] for p in collected]}")
        session = get_cached_database_provider().get_session_factory()()
        active_codes = {p["perm_code"] for p in collected}

        for perm in collected:
            existing = session.query(PermissionEntity).filter_by(perm_code=perm["perm_code"]).first()
            if existing:
                existing.perm_name = perm["perm_name"]
                existing.module = perm["module"]
                existing.operation = perm["operation"]
                existing.description = (perm["description"] or "")[:250]
                existing.is_deprecated = False
            else:
                p = dict(perm)
                p["description"] = (p.get("description") or "")[:250]
                session.add(PermissionEntity(**p, is_deprecated=False))

        deprecated = session.query(PermissionEntity).filter(
            PermissionEntity.is_deprecated == False,
            ~PermissionEntity.perm_code.in_(active_codes),
        ).all()
        for d in deprecated:
            d.is_deprecated = True
            logger.info(f"Permission deprecated (not found in routes): {d.perm_code}")

        session.commit()
        logger.info(f"Permissions auto-synced: {len(collected)} active, {len(deprecated)} deprecated")
    except Exception as e:
        logger.warning(f"Permission auto-sync failed: {e}")

    # 初始化通知子系统
    from src.notification.bootstrap import setup_notification_system
    retry_task = setup_notification_system()

    yield

    logger.info(f"{APP_NAME} shutting down...")

    if retry_task is not None:
        retry_task.cancel()
        try:
            await retry_task
        except Exception:
            pass

    get_cached_database_provider().close()
    logger.info("Database connection closed")

    get_cached_cache_provider().close()
    logger.info("Redis connection closed")


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

    # ============================================================
    # 中间件注册顺序（核心原则：后注册的在外层）
    # ============================================================
    #
    # FastAPI 中间件采用"洋葱模型"，请求从外层进入，响应从内层出来：
    #
    #   ┌─────────────────────────────────────────────────────────┐
    #   │  CORS (最外层)                                          │
    #   │  ┌─────────────────────────────────────────────────┐   │
    #   │  │  RequestID                                      │   │
    #   │  │  ┌─────────────────────────────────────────┐   │   │
    #   │  │  │  RequestLogging                         │   │   │
    #   │  │  │  ┌─────────────────────────────────┐   │   │   │
    #   │  │  │  │  ExceptionHandling (最内层)     │   │   │   │
    #   │  │  │  │  ┌─────────────────────────┐   │   │   │   │
    #   │  │  │  │  │     路由处理函数         │   │   │   │   │
    #   │  │  │  │  └─────────────────────────┘   │   │   │   │
    #   │  │  │  └─────────────────────────────────┘   │   │   │
    #   │  │  └─────────────────────────────────────────┘   │   │
    #   │  └─────────────────────────────────────────────────┘   │
    #   └─────────────────────────────────────────────────────────┘
    #
    #   请求进入顺序（外层先执行）：CORS → RequestID → RequestLogging → ExceptionHandling → 路由
    #   响应返回顺序（内层先返回）：路由 → ExceptionHandling → RequestLogging → RequestID → CORS
    #
    # 为什么要这样排列？
    #   - CORS 最外层：跨域请求在最开始就要处理，否则其他中间件都收不到请求
    #   - RequestID 次外层：尽早为请求打上唯一标识，后续日志都能关联
    #   - RequestLogging 中间层：记录请求信息，异常已被内层处理，不会记录异常堆栈
    #   - ExceptionHandling 最内层：作为最后一道防线，兜底处理所有未捕获的异常
    # ============================================================

    # 1. 最先注册 → 最内层（最早返回）→ 异常兜底
    app.add_middleware(ExceptionHandlingMiddleware)
    # 2. 请求日志记录
    app.add_middleware(RequestLoggingMiddleware)
    # 3. 请求ID生成与传递
    app.add_middleware(RequestIDMiddleware)
    # 4. 最后注册 → 最外层（最早执行） → CORS 跨域处理
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials="*" not in settings.cors.origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 限流器注册（在应用 state 上挂载 limiter，slowapi 通过装饰器使用）
    if _has_slowapi:
        setup_rate_limiter(app)
        logger.info(f"Rate limiter enabled: {settings.rate_limit.per_minute} req/min per IP")
    else:
        logger.info("Rate limiter disabled (slowapi not installed)")

    # 认证用户路由（面向用户，JWT 鉴权）
    app.include_router(api_router)

    # 开放平台路由（面向应用，AppId/AppKey 鉴权）
    app.include_router(open_router)

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

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=reload,
        workers=workers,
    )


if __name__ == "__main__":
    main()
