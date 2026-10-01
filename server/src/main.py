#!/usr/bin/env python3
"""
应用入口模块
本模块是 FastAPI 应用的核心入口，提供应用工厂函数和启动命令。
负责编排所有组件的初始化顺序：配置加载 → 日志初始化 → 中间件注册 →
异常处理器注册 → 路由挂载。

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
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router, open_router
from src.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logger import logger, setup_logging
from src.core.middleware import (
    ExceptionHandlingMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)
from src.infras.cache import get_cached_cache_provider
from src.infras.rate_limiter import get_cached_rate_limiter_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    setup_logging()
    logger.info(f"{APP_NAME} v{APP_VERSION} starting up (env={settings.app_env}, debug={settings.server.debug})")
    # 创建数据库引擎对象和连接池
    from src.infras.database import get_cached_database_provider

    get_cached_database_provider()
    # 初始化数据库（表）
    from src.infras.database import init_db

    init_db()
    logger.info("Database initialized successfully")
    # 初始化种子数据
    from src.core.seed import init_seed_data

    init_seed_data()
    # 初始化 Redis
    get_cached_cache_provider()
    logger.info("Redis connection established")
    # 自动扫描路由中的权限声明，同步到 permissions 表
    # 权限元数据（含描述 / 排序号）全部来自 PermissionCode 统一目录
    try:
        from src.api.api_permission_decorator import collect_permissions_from_app
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
                existing.description = perm["description"]
                existing.sort_order = perm["sort_order"]
                existing.is_deprecated = False
            else:
                session.add(PermissionEntity(**perm, is_deprecated=False))
        deprecated = (
            session.query(PermissionEntity)
            .filter(
                PermissionEntity.is_deprecated.is_(False),
                ~PermissionEntity.perm_code.in_(active_codes),
            )
            .all()
        )
        for d in deprecated:
            d.is_deprecated = True
            logger.info(f"Permission deprecated (not found in routes): {d.perm_code}")
        session.commit()
        logger.info(f"Permissions auto-synced: {len(collected)} active, {len(deprecated)} deprecated")
    except Exception as e:
        logger.warning(f"Permission auto-sync failed: {e}")
    # 自动扫描开放平台路由的 scope 声明，同步到 openapi_scopes 表
    try:
        from src.api.openapi_scope_decorator import collect_scopes_from_app
        from src.models.entities.app_entity import OpenApiScopeEntity

        collected_scopes = collect_scopes_from_app(app)
        logger.debug(f"Collected scopes: {[s['scope_code'] for s in collected_scopes]}")
        scope_session = get_cached_database_provider().get_session_factory()()
        active_scope_codes = {s["scope_code"] for s in collected_scopes}
        for idx, sc in enumerate(collected_scopes, start=1):
            existing = scope_session.query(OpenApiScopeEntity).filter_by(scope_code=sc["scope_code"]).first()
            if existing:
                existing.scope_name = sc["scope_name"]
                existing.module = sc["module"]
                existing.operation = sc["operation"]
                if sc["description"]:
                    existing.description = (sc["description"] or "")[:250]
                existing.sort_order = idx
                existing.is_deprecated = False
            else:
                s = dict(sc)
                s["description"] = (s.get("description") or "")[:250]
                s["sort_order"] = idx
                scope_session.add(OpenApiScopeEntity(**s, is_deprecated=False))
        deprecated_scopes = (
            scope_session.query(OpenApiScopeEntity)
            .filter(
                OpenApiScopeEntity.is_deprecated.is_(False),
                ~OpenApiScopeEntity.scope_code.in_(active_scope_codes),
            )
            .all()
        )
        for d in deprecated_scopes:
            d.is_deprecated = True
            logger.info(f"Scope deprecated (not found in routes): {d.scope_code}")
        scope_session.commit()
        logger.info(f"OpenAPI scopes auto-synced: {len(collected_scopes)} active, {len(deprecated_scopes)} deprecated")
    except Exception as e:
        logger.warning(f"OpenAPI scope auto-sync failed: {e}")
    # 初始化通知子系统
    from src.notification.bootstrap import setup_notification_system

    retry_task = setup_notification_system()
    yield
    logger.info(f"{APP_NAME} shutting down...")
    if retry_task is not None:
        retry_task.cancel()
        with suppress(asyncio.CancelledError):
            await retry_task
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
        6. 挂载 API 路由

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
    # 限流器注册（通过 RateLimiterProvider 抽象装配，当前实现基于 slowapi）
    get_cached_rate_limiter_provider().setup(app)
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
        "-V",
        "--version",
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
        "src.main:app",
        host=args.host,
        port=args.port,
        reload=reload,
        workers=workers,
    )


if __name__ == "__main__":
    main()
