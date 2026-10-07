#!/usr/bin/env python3
"""开放平台开发者资料与认证 DTO（个人中心，对应 api/open_portal/v1/developer.py）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeveloperProfileResponse(BaseModel):
    """开发者资料响应（个人中心）。"""

    id: int = Field(description="开发者ID")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str = Field(description="姓名/昵称")
    phone: str = Field(description="手机号")
    certification_type: str | None = Field(default=None, description="认证类型：personal/enterprise")
    certification_status: str = Field(description="认证状态：none/pending/approved/rejected")
    company_name: str | None = Field(default=None, description="企业名称")
    created_at: datetime = Field(description="注册时间")
    model_config = ConfigDict(from_attributes=True)


class DeveloperProfileUpdateRequest(BaseModel):
    """开发者资料更新请求。"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="姓名/昵称")
    phone: str | None = Field(default=None, min_length=5, max_length=20, description="手机号")


class DeveloperCertificationRequest(BaseModel):
    """开发者认证申请请求（预留）。"""

    certification_type: str = Field(pattern="^(personal|enterprise)$", description="认证类型")
    company_name: str | None = Field(default=None, max_length=200, description="企业名称（企业认证必填）")
    credential_no: str | None = Field(default=None, max_length=100, description="证件号")
