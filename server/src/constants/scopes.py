#!/usr/bin/env python3
"""开放平台 scope 统一目录（scope 元数据的唯一事实来源）。

Scope 的编码 / 中文名 / 所属模块 / 操作类型 / 描述 / 排序号全部在
OpenApiScopeCode 中定义一次；模块编码与中文名映射集中在 OpenApiScopeModule。
以下消费方均从本目录派生，禁止再硬编码 scope 码：
    - 开放平台 api 路由：@app_scope(OpenApiScopeCode.XXX) 挂载元数据，
      require_app_scope(OpenApiScopeCode.XXX.mark) 做鉴权
    - 启动时路由扫描同步（api/open/scope_decorator.sync_scopes_to_db）
    - 开放平台应用管理的 scope 勾选列表（openapi_app_service.list_scopes）

成员定义顺序即 scope 管理后台的展示顺序（sort_order 递增）。
动作词表保留 read / write 粗粒度（第三方集成惯例），与用户态权限的
view/create/edit/delete 细分动作体系相互独立。
"""

from __future__ import annotations

from src.constants.base import BaseEnum, StrBaseEnum


class OpenApiScopeModule(StrBaseEnum):
    """开放平台 scope 模块编码与中文名映射（与 OpenApiScopeCode.module 一一对应）。"""

    USER = ("user", "用户管理")


class OpenApiScopeAction(StrBaseEnum):
    """开放平台 scope 动作词表（scope 码冒号后缀的统一来源）。

    保留 read / write 粗粒度：面向第三方集成方，授权勾选简单；
    不随用户态权限拆分为 view/create/edit/delete。
    """

    READ = ("read", "读取")
    WRITE = ("write", "写入")


class OpenApiScopeCode(BaseEnum):
    """开放平台 scope 编码及元数据。

    成员值为 6 元组：
        (scope_code, scope_name, module, operation, description, sort_order)
    其中 mark（继承自 BaseEnum）即 scope_code，desc 即 scope_name，
    可直接与裸字符串比较（OpenApiScopeCode.USER_READ == "user:read"）。
    """

    def __init__(
        self,
        mark: str,
        scope_name: str,
        module: str,
        operation: str,
        description: str,
        sort_order: int,
    ) -> None:
        super().__init__(mark, scope_name)
        self._scope_name = scope_name
        self._module = module
        self._operation = operation
        self._description = description
        self._sort_order = sort_order

    @property
    def scope_name(self) -> str:
        """scope 中文名。"""
        return self._scope_name

    @property
    def module(self) -> str:
        """所属模块编码。"""
        return self._module

    @property
    def operation(self) -> str:
        """操作类型。"""
        return self._operation

    @property
    def description(self) -> str:
        """scope 描述。"""
        return self._description

    @property
    def sort_order(self) -> int:
        """展示排序号。"""
        return self._sort_order

    # ── 用户域 ────────────────────────────────────────────
    USER_READ = ("user:read", "读取用户数据", OpenApiScopeModule.USER.mark, OpenApiScopeAction.READ.mark, "查询开放平台用户列表与详情", 1)
    USER_WRITE = ("user:write", "写入用户数据", OpenApiScopeModule.USER.mark, OpenApiScopeAction.WRITE.mark, "创建、更新或删除开放平台用户", 2)


#: scope 目录（成员定义顺序），供种子初始化等批量场景遍历
OPENAPI_SCOPE_CATALOG: tuple[OpenApiScopeCode, ...] = tuple(OpenApiScopeCode)


__all__ = ["OpenApiScopeModule", "OpenApiScopeAction", "OpenApiScopeCode", "OPENAPI_SCOPE_CATALOG"]
