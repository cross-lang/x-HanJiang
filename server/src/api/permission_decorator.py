#!/usr/bin/env python3
"""权限装饰器。

用法：
    @router.get("", dependencies=[Depends(require_user_permission("user:view"))])
    @permission("user:view", "查看用户", "user", "view")
    async def list_users():
        ...

启动时自动扫描所有路由的 _permission_code 属性，upsert 到 permissions 表。
"""

from typing import Callable


def permission(code: str, name: str = "", module: str = "", operation: str = ""):
    """声明路由所需权限（仅挂载元数据，鉴权仍用 Depends）。

    Args:
        code: 权限编码，如 user:view
        name: 权限中文名，如 查看用户
        module: 模块名，如 user
        operation: 操作类型，如 view
    """

    def decorator(func: Callable):
        func._permission_code = code
        func._permission_name = name
        func._permission_module = module
        func._permission_operation = operation
        return func

    return decorator


def collect_permissions_from_app(app) -> list[dict]:
    """扫描 FastAPI 应用所有路由，收集带 @permission 装饰器的权限元数据。"""
    permissions = []
    for route in app.routes:
        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            path = getattr(route, "path", "?")
            if hasattr(endpoint, "_permission_code"):
                print(f">>> Found perm: {endpoint._permission_code} at {path}", flush=True)
                permissions.append({
                    "perm_code": endpoint._permission_code,
                    "perm_name": endpoint._permission_name or endpoint._permission_code,
                    "module": endpoint._permission_module or "",
                    "operation": endpoint._permission_operation or "",
                    "description": (endpoint.__doc__ or "")[:250],
                })
            else:
                print(f">>> No perm attr: {path} -> {endpoint.__name__}", flush=True)
    # 按 perm_code 去重（多个路由共用同一权限码时只保留一条）
    seen = set()
    unique = []
    for p in permissions:
        if p["perm_code"] not in seen:
            seen.add(p["perm_code"])
            unique.append(p)
    return unique
