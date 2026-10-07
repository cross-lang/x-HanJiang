#!/usr/bin/env python3
"""开放平台开发者认证 DTO。

注册/登录/令牌/改密等认证域模型；当前开发者鉴权上下文（CurrentDeveloper）亦在此维护。
开发者资料域（个人中心）模型见 developer.py。
"""

from pydantic import BaseModel, ConfigDict, Field


class DeveloperRegisterRequest(BaseModel):
    """开发者注册请求（所有字段均为必填）。"""

    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: str = Field(min_length=3, max_length=100, description="邮箱")
    password: str = Field(min_length=8, max_length=64, description="密码")
    confirm_password: str = Field(min_length=8, max_length=64, description="确认密码")
    name: str = Field(min_length=1, max_length=100, description="昵称（必填）")
    certification_type: str = Field(
        pattern="^(personal|enterprise)$",
        description="认证主体类型：personal 个人 / enterprise 企业",
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


class DeveloperForgotPasswordRequest(BaseModel):
    """开发者忘记密码：提交注册邮箱，触发重置邮件。"""

    email: str = Field(min_length=3, max_length=100, description="注册邮箱")


class DeveloperResetPasswordRequest(BaseModel):
    """开发者重置密码：携带邮件中的重置令牌 + 新密码。"""

    token: str = Field(min_length=1, description="邮件中携带的重置令牌")
    new_password: str = Field(min_length=8, max_length=64, description="新密码")
    confirm_password: str = Field(min_length=8, max_length=64, description="确认密码")


class CurrentDeveloper(BaseModel):
    """当前登录开发者（JWT 鉴权后的最小上下文）。"""

    id: int = Field(description="开发者ID")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str = Field(description="姓名/昵称")
    phone: str = Field(description="手机号")
    status: str = Field(description="账号状态")
    model_config = ConfigDict(from_attributes=True)
