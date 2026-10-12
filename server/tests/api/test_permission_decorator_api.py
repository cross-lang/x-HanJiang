#!/usr/bin/env python3
"""权限装饰器（src/api/admin/permission_decorator.py）单元测试。

不发起真实 HTTP 请求，直接构造 FastAPI 应用挂载带 @permission 装饰器的路由，
验证：
    - @permission 在函数上挂载完整权限元数据；
    - collect_permissions_from_app 扫描路由并按 perm_code 去重；
    - 未装饰的路由被忽略。
"""

import importlib.util
from pathlib import Path

from fastapi import FastAPI
from src.constants.permissions import PermissionCode


def _load_decorator_module(module_name: str, rel: str):
    """按文件路径直接加载装饰器模块到独立名字，不触发 src.api.admin 包 __init__。

    src.api.admin.__init__ 会聚合全部 v1 路由并间接 import bcrypt；若走常规
    ``from src.api.admin.permission_decorator import ...``，在同一进程与开放路由链
    同时收集时会触发 bcrypt 原生模块二次初始化报错，且占位 sys.modules 会污染
    test_health 等依赖完整应用的用例。这里用 importlib 直接按文件加载，
    装饰器模块本身只依赖 fastapi 与常量目录，无需路由链。
    """
    path = Path(__file__).resolve().parent / rel
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_perm_mod = _load_decorator_module("_permission_decorator_under_test", "../../src/api/admin/permission_decorator.py")
permission = _perm_mod.permission
collect_permissions_from_app = _perm_mod.collect_permissions_from_app


def test_permission_decorator_attaches_metadata() -> None:
    """@permission 把权限码及其元数据挂载到函数对象上。"""

    @permission(PermissionCode.USER_VIEW)
    def handler() -> dict:
        return {}

    assert handler._permission_code == PermissionCode.USER_VIEW.mark
    assert handler._permission_name == PermissionCode.USER_VIEW.perm_name
    assert handler._permission_module == PermissionCode.USER_VIEW.module
    assert handler._permission_operation == PermissionCode.USER_VIEW.operation
    assert handler._permission_description == PermissionCode.USER_VIEW.description
    assert handler._permission_sort_order == PermissionCode.USER_VIEW.sort_order


def test_collect_permissions_from_app_dedup() -> None:
    """扫描应用路由：仅收集带装饰器的路由，同权限码多路由只保留一条。"""
    app = FastAPI()

    @app.get("/users")
    @permission(PermissionCode.USER_VIEW)
    async def list_users() -> dict:
        return {}

    @app.get("/users/detail")
    @permission(PermissionCode.USER_VIEW)
    async def user_detail() -> dict:
        return {}

    @app.get("/roles")
    @permission(PermissionCode.ROLE_VIEW)
    async def list_roles() -> dict:
        return {}

    @app.get("/health")
    async def health() -> dict:
        return {}

    collected = collect_permissions_from_app(app)
    codes = {p["perm_code"] for p in collected}
    # 两个路由共用 user:view → 去重后只剩两个不同权限码
    assert codes == {PermissionCode.USER_VIEW.mark, PermissionCode.ROLE_VIEW.mark}
    assert len(collected) == 2
    # 元数据完整
    user_view = next(p for p in collected if p["perm_code"] == PermissionCode.USER_VIEW.mark)
    assert user_view["module"] == PermissionCode.USER_VIEW.module
    assert user_view["sort_order"] == PermissionCode.USER_VIEW.sort_order


def test_collect_permissions_empty_app() -> None:
    """无任何带装饰器路由时返回空列表。"""
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        return {}

    assert collect_permissions_from_app(app) == []
