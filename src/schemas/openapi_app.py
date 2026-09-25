#!/usr/bin/env python3
"""开放平台应用 DTO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OpenApiAppCreateRequest(BaseModel):
    """管理员创建开放应用请求。"""

    name: str = Field(min_length=1, max_length=100, description="应用名")
    scopes: list[str] = Field(default_factory=list, description="权限范围列表，如 ['ping:read']")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=100000)
    auth_mode: str = Field(default="plain", pattern="^(plain|hmac|both)$")


class OpenApiAppUpdateRequest(BaseModel):
    """管理员更新开放应用（改 scope / 限流 / 鉴权模式 / 状态）。"""

    name: str | None = Field(default=None, max_length=100)
    scopes: list[str] | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=100000)
    auth_mode: str | None = Field(default=None, pattern="^(plain|hmac|both)$")
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


class OpenApiAppResponse(BaseModel):
    """应用列表/详情响应（绝不返回 AppKey 明文）。"""

    id: int
    app_id: str
    name: str
    scopes: list[str]
    status: str
    auth_mode: str
    rate_limit_per_minute: int
    owner_user_id: int | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpenApiAppCreatedResponse(OpenApiAppResponse):
    """创建应用成功响应——唯一一次返回明文 AppKey。"""

    app_key: str = Field(description="明文 AppKey，仅本次返回，后续无法再查看")


class CurrentApp(BaseModel):
    """当前调用方应用（机器身份，无终端用户上下文）。"""

    app_id: str
    name: str
    scopes: list[str]
    auth_mode: str
    rate_limit_per_minute: int
