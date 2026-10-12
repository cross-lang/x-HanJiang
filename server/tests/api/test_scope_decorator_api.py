#!/usr/bin/env python3
"""开放 API scope 装饰器（src/api/open/scope_decorator.py）单元测试。

直接构造 FastAPI 应用挂载带 @app_scope 装饰器的路由，验证：
    - @app_scope 在函数上挂载完整 scope 元数据；
    - collect_scopes_from_app 扫描路由并按 scope_code 去重；
    - 未装饰的路由被忽略。
"""

import importlib.util
from pathlib import Path

from fastapi import FastAPI
from src.constants.scopes import OpenApiScopeCode


def _load_decorator_module(module_name: str, rel: str):
    """按文件路径直接加载 scope 装饰器模块到独立名字，不触发 src.api.open 包 __init__。

    src.api.open.__init__ 会聚合全部 v1 路由并间接 import bcrypt；走常规导入会在
    同一进程与管理端路由链同时收集时触发 bcrypt 原生模块二次初始化报错。
    这里用 importlib 直接按文件加载，scope 装饰器模块只依赖 fastapi 与 scope 常量。
    """
    path = Path(__file__).resolve().parent / rel
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_scope_mod = _load_decorator_module("_scope_decorator_under_test", "../../src/api/open/scope_decorator.py")
app_scope = _scope_mod.app_scope
collect_scopes_from_app = _scope_mod.collect_scopes_from_app


def test_app_scope_decorator_attaches_metadata() -> None:
    """@app_scope 把 scope 码及其元数据挂载到函数对象上。"""

    @app_scope(OpenApiScopeCode.USER_READ)
    def handler() -> dict:
        return {}

    assert handler._scope_code == OpenApiScopeCode.USER_READ.mark
    assert handler._scope_name == OpenApiScopeCode.USER_READ.scope_name
    assert handler._scope_module == OpenApiScopeCode.USER_READ.module
    assert handler._scope_operation == OpenApiScopeCode.USER_READ.operation
    assert handler._scope_description == OpenApiScopeCode.USER_READ.description
    assert handler._scope_sort_order == OpenApiScopeCode.USER_READ.sort_order


def test_collect_scopes_from_app_dedup() -> None:
    """扫描应用路由：仅收集带装饰器的路由，同 scope 码多路由只保留一条。"""
    app = FastAPI()

    @app.get("/users")
    @app_scope(OpenApiScopeCode.USER_READ)
    async def list_users() -> dict:
        return {}

    @app.get("/users/detail")
    @app_scope(OpenApiScopeCode.USER_READ)
    async def user_detail() -> dict:
        return {}

    @app.get("/files")
    @app_scope(OpenApiScopeCode.FILE_READ)
    async def list_files() -> dict:
        return {}

    @app.get("/health")
    async def health() -> dict:
        return {}

    collected = collect_scopes_from_app(app)
    codes = {s["scope_code"] for s in collected}
    assert codes == {OpenApiScopeCode.USER_READ.mark, OpenApiScopeCode.FILE_READ.mark}
    assert len(collected) == 2
    user_read = next(s for s in collected if s["scope_code"] == OpenApiScopeCode.USER_READ.mark)
    assert user_read["module"] == OpenApiScopeCode.USER_READ.module
    assert user_read["sort_order"] == OpenApiScopeCode.USER_READ.sort_order


def test_collect_scopes_empty_app() -> None:
    """无任何带装饰器路由时返回空列表。"""
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        return {}

    assert collect_scopes_from_app(app) == []
