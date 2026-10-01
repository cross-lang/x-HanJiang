#!/usr/bin/env python3
"""权限装饰器。
用法：
    @router.get("", dependencies=[Depends(require_user_permission(PermissionCode.USER_VIEW.mark))])
    @permission(PermissionCode.USER_VIEW)
    async def list_users():
        ...
启动时自动扫描所有路由的 _permission_* 属性，upsert 到 permissions 表。
权限的全部元数据均来自 src.constants.permissions.PermissionCode 统一目录。
"""

from collections.abc import Callable

from src.constants.permissions import PermissionCode
from src.core.logger import logger


def permission(code: PermissionCode):
    """声明路由所需权限（仅挂载元数据，鉴权仍用 Depends）。

    Args:
        code: PermissionCode 枚举成员，携带权限码 / 中文名 / 模块 /
              操作类型 / 描述 / 排序号全部元数据
    """

    def decorator(func: Callable):
        func._permission_code = code.mark
        func._permission_name = code.perm_name
        func._permission_module = code.module
        func._permission_operation = code.operation
        func._permission_description = code.description
        func._permission_sort_order = code.sort_order
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
                logger.debug(f"Found permission: {endpoint._permission_code} at {path}")
                permissions.append(
                    {
                        "perm_code": endpoint._permission_code,
                        "perm_name": endpoint._permission_name or endpoint._permission_code,
                        "module": endpoint._permission_module or "",
                        "operation": endpoint._permission_operation or "",
                        "description": endpoint._permission_description or "",
                        "sort_order": endpoint._permission_sort_order,
                    }
                )
            else:
                logger.debug(f"No permission decorator: {path} -> {endpoint.__name__}")
    # 按 perm_code 去重（多个路由共用同一权限码时只保留一条）
    seen = set()
    unique = []
    for p in permissions:
        if p["perm_code"] not in seen:
            seen.add(p["perm_code"])
            unique.append(p)
    return unique
