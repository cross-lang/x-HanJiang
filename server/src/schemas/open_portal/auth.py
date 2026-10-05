#!/usr/bin/env python3
"""开放平台开发者认证 DTO。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeveloperRegisterRequest(BaseModel):
    """开发者注册请求。"""

    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: str = Field(min_length=3, max_length=100, description="邮箱")
    password: str = Field(min_length=8, max_length=64, description="密码")
    confirm_password: str = Field(min_length=8, max_length=64, description="确认密码")
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="昵称（注册时可选，为空时回退为用户名）",
    )
    certification_type: str | None = Field(
        default=None,
        pattern="^(personal|enterprise)$",
        description="认证主体类型（预留，注册时可不填）",
    )


class DeveloperLoginRequest(BaseModel):
    """开发者登录请求（账号=用户名或邮箱）。"""

    account: str = Field(min_length=1, max_length=100, description="用户名或邮箱")
    password: str = Field(min_length=1, max_length=64, description="密码")
    model_config = ConfigDict(from_attributes=True)


class DeveloperRefreshRequest(BaseModel):
    """开发者刷新令牌请求。"""

    refresh_token: str = Field(min_length=1, description="刷新令牌")


class DeveloperTokenResponse(BaseModel):
    """开发者登录令牌响应（有状态会话：JWT + Redis 登录态，登出/改密后可撤销）。"""

    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌（用于续期，登出后失效）")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(description="访问令牌有效期（秒）")


class DeveloperChangePasswordRequest(BaseModel):
    """开发者修改密码请求。"""

    old_password: str = Field(min_length=1, max_length=64, description="原密码")
    new_password: str = Field(min_length=8, max_length=64, description="新密码")


class CurrentDeveloper(BaseModel):
    """当前登录开发者（JWT 鉴权后的最小上下文）。"""

    id: int = Field(description="开发者ID")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str = Field(description="姓名/昵称")
    phone: str = Field(description="手机号")
    status: str = Field(description="账号状态")
    model_config = ConfigDict(from_attributes=True)


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
