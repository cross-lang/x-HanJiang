#!/usr/bin/env python3
"""
管理端角色权限特有 DTO。

双渠道共享的角色/权限模型（RoleResponse / PermissionResponse /
RolePermissionResponse / RoleCreateRequest / RoleUpdateRequest）
位于 schemas/role.py；本文件仅保留管理系统渠道特有的请求模型。

Classes:
    PermissionCreateRequest: 创建权限请求模型（权限管理页为只读，预留）
    PermissionUpdateRequest: 更新权限请求模型（预留）
    BindPermissionRequest: 角色绑定权限请求模型
"""

from pydantic import BaseModel, Field


class PermissionCreateRequest(BaseModel):
    """创建权限请求模型。"""

    perm_code: str = Field(min_length=1, max_length=50, description="权限编码")
    perm_name: str = Field(min_length=1, max_length=50, description="权限名称")
    module: str = Field(default="", max_length=50, description="所属模块")
    operation: str = Field(default="", max_length=50, description="操作类型")
    description: str | None = Field(default=None, max_length=255, description="权限说明")
    sort_order: int = Field(default=0, description="排序序号")


class PermissionUpdateRequest(BaseModel):
    """更新权限请求模型（字段可选，仅更新传入字段）。"""

    perm_code: str | None = Field(default=None, min_length=1, max_length=50, description="权限编码")
    perm_name: str | None = Field(default=None, min_length=1, max_length=50, description="权限名称")
    module: str | None = Field(default=None, max_length=50, description="所属模块")
    operation: str | None = Field(default=None, max_length=50, description="操作类型")
    description: str | None = Field(default=None, max_length=255, description="权限说明")
    sort_order: int | None = Field(default=None, description="排序序号")


class BindPermissionRequest(BaseModel):
    """角色绑定权限请求模型。"""

    permission_id: int = Field(description="要绑定的权限 ID")
