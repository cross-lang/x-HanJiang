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
from typing import Any, ParamSpec, TypeVar

from fastapi import FastAPI

from src.constants.permissions import PermissionCode
from src.core.logger import logger

_P = ParamSpec("_P")
_R = TypeVar("_R")


def permission(code: PermissionCode) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """声明路由所需权限（仅挂载元数据，鉴权仍用 Depends）。

    Args:
        code: PermissionCode 枚举成员，携带权限码 / 中文名 / 模块 /
              操作类型 / 描述 / 排序号全部元数据

    Returns:
        保持原函数签名的装饰器。
    """

    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
        func._permission_code = code.mark
        func._permission_name = code.perm_name
        func._permission_module = code.module
        func._permission_operation = code.operation
        func._permission_description = code.description
        func._permission_sort_order = code.sort_order
        return func

    return decorator


def collect_permissions_from_app(app: FastAPI) -> list[dict[str, Any]]:
    """扫描 FastAPI 应用所有路由，收集带 @permission 装饰器的权限元数据。

    Args:
        app: FastAPI 应用实例

    Returns:
        权限元数据字典列表（perm_code / perm_name / module / operation /
        description / sort_order），按 perm_code 去重。
    """
    permissions: list[dict[str, Any]] = []
    for route in app.routes:
        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            path = getattr(route, "path", "?")
            perm_code = getattr(endpoint, "_permission_code", None)
            if perm_code is not None:
                logger.debug(f"Found permission: {perm_code} at {path}")
                permissions.append(
                    {
                        "perm_code": perm_code,
                        "perm_name": getattr(endpoint, "_permission_name", None) or perm_code,
                        "module": getattr(endpoint, "_permission_module", None) or "",
                        "operation": getattr(endpoint, "_permission_operation", None) or "",
                        "description": getattr(endpoint, "_permission_description", None) or "",
                        "sort_order": getattr(endpoint, "_permission_sort_order", 0),
                    }
                )
            else:
                logger.debug(f"No permission decorator: {path} -> {endpoint.__name__}")
    # 按 perm_code 去重（多个路由共用同一权限码时只保留一条）
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for p in permissions:
        if p["perm_code"] not in seen:
            seen.add(p["perm_code"])
            unique.append(p)
    return unique


def sync_permissions_to_db(app: FastAPI) -> tuple[int, int]:
    """启动时将路由上的 @permission 声明对账同步到 permissions 表。

    以代码中的 PermissionCode 声明为唯一事实来源：
      - 代码中存在、表中已存在 → 按最新元数据更新并取消废弃标记；
      - 代码中存在、表中不存在 → 新增；
      - 表中存在、代码中已不存在 → 标记 is_deprecated=True（不物理删除）。
    任一步骤失败由 session 上下文自动回滚并向上抛出，由调用方决定是否阻断启动。

    Args:
        app: FastAPI 应用实例

    Returns:
        (active_count, deprecated_count): 本次启用权限数与新标记废弃权限数
    """
    from src.infras.database import get_cached_database_provider
    from src.models.entities.user_entity import PermissionEntity

    collected = collect_permissions_from_app(app)
    logger.debug(f"Collected permissions: {[p['perm_code'] for p in collected]}")
    active_codes = {p["perm_code"] for p in collected}

    with get_cached_database_provider().session() as session:
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

    logger.info(f"Permissions auto-synced: {len(collected)} active, {len(deprecated)} deprecated")
    return len(collected), len(deprecated)


__all__ = ["permission", "collect_permissions_from_app", "sync_permissions_to_db"]
