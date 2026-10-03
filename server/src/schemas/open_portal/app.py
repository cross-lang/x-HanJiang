#!/usr/bin/env python3
"""开放平台开发者应用 DTO（开发者门户视角，与管理端 schema 分离）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OpenAppCreateRequest(BaseModel):
    """开发者创建应用请求。"""

    name: str = Field(min_length=1, max_length=100, description="应用名")
    description: str = Field(min_length=1, max_length=255, description="应用描述")
    scopes: list[str] = Field(min_length=1, description="申请权限范围，至少 1 个")
    auth_mode: str = Field(default="plain", pattern="^(plain|hmac|both)$", description="鉴权模式")


class OpenAppUpdateRequest(BaseModel):
    """开发者更新应用（仅基本信息，scope 走独立申请端点）。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=255)
    auth_mode: str | None = Field(default=None, pattern="^(plain|hmac|both)$")


class OpenAppScopeApplyRequest(BaseModel):
    """开发者提交 scope 申请/调整。"""

    scopes: list[str] = Field(min_length=1, description="申请权限范围，至少 1 个")
    reason: str | None = Field(default=None, max_length=255, description="申请说明")


class OpenAppResponse(BaseModel):
    """开发者应用响应（绝不返回 AppKey 明文）。"""

    id: int
    app_id: str
    name: str
    description: str
    scopes: list[str]
    auth_mode: str
    status: str
    # 归属与审批
    owner_type: str
    owner_id: int | None
    approval_status: str
    approval_note: str | None
    last_used_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OpenAppCreatedResponse(OpenAppResponse):
    """创建应用成功响应——唯一一次返回明文 AppKey。"""

    app_key: str = Field(description="明文 AppKey，仅本次返回，后续无法再查看")


class OpenAppSecretResponse(BaseModel):
    """AppKey 重置响应。"""

    app_id: str = Field(description="应用 ID")
    app_key: str = Field(description="新明文 AppKey，仅本次返回")
    warning: str = Field(default="新 AppKey 仅本次返回", description="提示")
