#!/usr/bin/env python3
"""权限装饰器。

用法：
    @router.get("")
    @permission("user:view", "查看用户", "user", "view")
    async def list_users():
        ...

启动时自动扫描所有路由的 _permission_code 属性，upsert 到 permissions 表。
"""

from functools import wraps
from typing import Callable

from fastapi import Depends, Request

from src.api.dependencies import get_current_user, get_permission_service
from src.core.exceptions import AuthorizationException
from src.schemas.auth import CurrentUser


def permission(code: str, name: str = "", module: str = "", operation: str = ""):
    """声明路由所需权限，同时完成鉴权。

    Args:
        code: 权限编码，如 user:view
        name: 权限中文名，如 查看用户
        module: 模块名，如 user
        operation: 操作类型，如 view
    """

    def decorator(func: Callable):
        # 挂元数据到函数上，启动时扫描
        func._permission_code = code
        func._permission_name = name
        func._permission_module = module
        func._permission_operation = operation

        @wraps(func)
        async def wrapper(
            *args,
            current_user: CurrentUser = Depends(get_current_user),
            permission_service=Depends(get_permission_service),
            **kwargs,
        ):
            if not permission_service.has_permission(current_user.id, code):
                raise AuthorizationException(message=f"缺少权限: {code}")
            return await func(*args, **kwargs)

        # 把元数据也挂到 wrapper 上
        wrapper._permission_code = code
        wrapper._permission_name = name
        wrapper._permission_module = module
        wrapper._permission_operation = operation
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def collect_permissions_from_app(app) -> list[dict]:
    """扫描 FastAPI 应用所有路由，收集带 @permission 装饰器的权限元数据。"""
    permissions = []
    for route in app.routes:
        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            if hasattr(endpoint, "_permission_code"):
                permissions.append({
                    "perm_code": endpoint._permission_code,
                    "perm_name": endpoint._permission_name or endpoint._permission_code,
                    "module": endpoint._permission_module or "",
                    "operation": endpoint._permission_operation or "",
                    "description": endpoint.__doc__ or "",
                })
    return permissions
