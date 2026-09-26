#!/usr/bin/env python3
"""
角色与权限数据模型

本模块定义角色、权限及角色权限关联相关的请求和响应数据传输对象（DTO）。

Classes:
    RoleResponse: 角色响应模型
    PermissionResponse: 权限响应模型
    RolePermissionResponse: 角色权限关联响应模型
    RoleCreateRequest: 角色创建请求模型
    RoleUpdateRequest: 角色更新请求模型
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    """角色响应模型。"""

    id: int = Field(description="角色唯一标识")
    role_name: str = Field(description="角色名称")
    role_code: str = Field(description="角色编码")
    description: str | None = Field(default=None, description="角色描述")
    role_type: str = Field(description="角色类型（system/custom）")
    status: str = Field(description="状态（enabled/disabled）")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    """权限响应模型。"""

    id: int = Field(description="权限唯一标识")
    perm_code: str = Field(description="权限编码")
    perm_name: str = Field(description="权限名称")
    module: str = Field(description="所属模块")
    operation: str = Field(description="操作类型")
    description: str | None = Field(default=None, description="权限说明")
    sort_order: int = Field(default=0, description="排序序号")

    model_config = ConfigDict(from_attributes=True)


class RolePermissionResponse(BaseModel):
    """角色权限关联响应模型（含权限详情）。"""

    role_id: int = Field(description="角色ID")
    permission: PermissionResponse = Field(description="权限详情")

    model_config = ConfigDict(from_attributes=True)


class RoleCreateRequest(BaseModel):
    """角色创建请求模型。"""

    role_name: str = Field(min_length=1, max_length=50, description="角色名称")
    role_code: str = Field(min_length=1, max_length=50, description="角色编码")
    description: str | None = Field(default=None, max_length=255, description="角色描述")
    role_type: str = Field(default="custom", description="角色类型（system/custom）")
    status: str = Field(default="enabled", description="状态（enabled/disabled）")

    model_config = ConfigDict(from_attributes=True)


class RoleUpdateRequest(BaseModel):
    """角色更新请求模型（字段可选）。"""

    role_name: str | None = Field(default=None, min_length=1, max_length=50, description="角色名称")
    description: str | None = Field(default=None, max_length=255, description="角色描述")
    status: str | None = Field(default=None, description="状态（enabled/disabled）")

    model_config = ConfigDict(from_attributes=True)


class BindPermissionRequest(BaseModel):
    """角色绑定权限请求模型。"""

    permission_id: int = Field(description="要绑定的权限 ID")
