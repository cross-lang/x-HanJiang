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
    """开发者应用响应（绝不返回 AppKey 明文）。

    审批信息由服务层从应用申请表派生：
    - approved: 应用当前是否已通过创建审批（网关放行门槛）；
    - approval_status: 派生审批状态（pending 有待审批申请 / approved 已通过 /
      rejected 最近一次申请被驳回 / none 无申请记录）；
    - pending_registration_id: 当前待审批申请的申请ID（批次号），无则 None。
    """

    id: int
    app_id: str
    name: str
    description: str
    scopes: list[str]
    auth_mode: str
    status: str
    owner_type: str
    owner_id: int | None
    approved: bool
    approval_status: str | None
    pending_registration_id: int | None = None
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


class OpenAppApprovalResponse(BaseModel):
    """应用审批记录（开发者门户视角，对应 openapi_app_registrations 批次）。

    应用每发起一次创建/修改（含 scope 调整）申请即生成一条批次记录，
    审批结果（审批人 / 意见 / 时间）随批次留痕，本 DTO 用于"全部审批记录"展示。
    """

    id: int = Field(description="申请ID（批次号，内部主键）")
    registration_code: str = Field(description="申请码：6位数字，对外展示用")
    app_id: int
    registration_type: str = Field(description="申请类型：create 创建申请 / update 修改申请")
    name: str
    description: str
    scopes: list[str] = Field(description="本次申请/授权的权限范围")
    auth_mode: str
    reason: str | None = Field(default=None, description="申请说明/用途")
    status: str = Field(description="pending 待审批 / approved 已通过 / rejected 已驳回")
    approver_name: str | None = Field(default=None, description="审批人姓名")
    note: str | None = Field(default=None, description="审批意见/驳回原因")
    created_at: datetime
    reviewed_at: datetime | None = Field(default=None, description="审批时间")
    model_config = ConfigDict(from_attributes=True)
