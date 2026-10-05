#!/usr/bin/env python3
"""开放平台应用 DTO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OpenApiAppCreateRequest(BaseModel):
    """管理员创建开放应用请求。"""

    name: str = Field(min_length=1, max_length=100, description="应用名")
    description: str = Field(max_length=255, description="应用描述")
    scopes: list[str] = Field(min_length=1, description="权限范围列表，至少 1 个，如 ['ping:read']")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=100000)
    auth_mode: str = Field(default="plain", pattern="^(plain|hmac|both)$")


class OpenApiAppUpdateRequest(BaseModel):
    """管理员更新开放应用（名称/描述/限流/鉴权模式）。

    启停状态走独立 PUT /{app_id}/status 端点；scope 变更走独立
    PUT /{app_id}/scopes 端点（含目录合法性校验与审批语义），
    通用编辑不接收 scopes，避免绕过 scope 校验/审批直接写入。
    """

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=100000)
    auth_mode: str | None = Field(default=None, pattern="^(plain|hmac|both)$")


class OpenApiAppStatusUpdateRequest(BaseModel):
    """管理员启停开放应用请求。"""

    status: str = Field(pattern="^(active|disabled)$")


class OpenApiAppScopesUpdateRequest(BaseModel):
    """覆盖更新应用 scope 列表。"""

    scopes: list[str] = Field(description="最新 scope 列表，会完全覆盖原有值")


class OpenApiAppApprovalRequest(BaseModel):
    """审批开发者 scope 申请。"""

    approved: bool = Field(description="是否通过（true 通过 / false 驳回）")
    note: str | None = Field(default=None, max_length=255, description="审批意见/驳回原因")


class OpenApiAppResponse(BaseModel):
    """应用列表/详情响应（绝不返回 AppKey 明文）。"""

    id: int
    app_id: str
    name: str
    description: str
    scopes: list[str]
    status: str
    auth_mode: str
    rate_limit_per_minute: int
    owner_type: str
    owner_id: int | None
    owner_name: str | None = None
    approval_status: str | None
    approved_by: int | None = None
    approval_note: str | None = None
    last_used_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OpenApiAppCreatedResponse(OpenApiAppResponse):
    """创建应用成功响应——唯一一次返回明文 AppKey。"""

    app_key: str = Field(description="明文 AppKey，仅本次返回，后续无法再查看")
