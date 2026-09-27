#!/usr/bin/env python3
"""开放平台 scope 装饰器。

用法：
    @router.get("/users", dependencies=[Depends(require_app_scope("user:read"))])
    @app_scope("user:read", "读取用户列表", "user", "read")
    async def list_users():
        ...

启动时自动扫描开放平台路由的 _scope_code 属性，upsert 到 openapi_scopes 表。
"""

from typing import Callable

from src.core.logger import logger


def app_scope(code: str, name: str = "", module: str = "", operation: str = ""):
    """声明开放平台路由所需 scope（仅挂载元数据，鉴权仍用 Depends(require_app_scope(...))）。

    Args:
        code: scope 编码，如 user:read
        name: scope 中文名，如 读取用户列表
        module: 模块名，如 user
        operation: 操作类型，如 read
    """

    def decorator(func: Callable):
        func._scope_code = code
        func._scope_name = name
        func._scope_module = module
        func._scope_operation = operation
        return func

    return decorator


def collect_scopes_from_app(app) -> list[dict]:
    """扫描 FastAPI 应用所有路由，收集带 @app_scope 装饰器的 scope 元数据。"""
    scopes = []
    for route in app.routes:
        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            path = getattr(route, "path", "?")
            if hasattr(endpoint, "_scope_code"):
                logger.debug(f"Found app scope: {endpoint._scope_code} at {path}")
                scopes.append({
                    "scope_code": endpoint._scope_code,
                    "scope_name": endpoint._scope_name or endpoint._scope_code,
                    "module": endpoint._scope_module or "",
                    "operation": endpoint._scope_operation or "",
                    "description": (endpoint.__doc__ or "")[:250],
                })
    # 按 scope_code 去重
    seen = set()
    unique = []
    for s in scopes:
        if s["scope_code"] not in seen:
            seen.add(s["scope_code"])
            unique.append(s)
    return unique
