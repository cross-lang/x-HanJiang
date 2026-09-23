#!/usr/bin/env python3
"""
认证数据模型

本模块定义认证（登录/刷新令牌/当前用户）相关的请求和响应 DTO。

Classes:
    LoginRequest: 登录请求模型
    TokenResponse: 令牌响应模型
    RefreshTokenRequest: 刷新令牌请求模型
    CurrentUserResponse: 当前用户信息响应模型
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """登录请求模型。

    支持用户名或邮箱 + 密码登录。

    Attributes:
        username: 用户名或邮箱
        password: 密码
        client_type: 登录端类型（console=后台管理端）
    """

    username: str = Field(min_length=3, max_length=100, description="用户名或邮箱")
    password: str = Field(min_length=1, max_length=64, description="密码")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """令牌响应模型。

    Attributes:
        access_token: 访问令牌
        refresh_token: 刷新令牌
        token_type: 令牌类型（固定 Bearer）
        expires_in: 访问令牌有效期（秒）
    """

    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(description="访问令牌有效期（秒）")

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型。

    Attributes:
        refresh_token: 刷新令牌
    """

    refresh_token: str = Field(min_length=10, description="刷新令牌")

    model_config = ConfigDict(from_attributes=True)


class CurrentUserResponse(BaseModel):
    """当前用户信息响应模型。

    Attributes:
        id: 用户ID
        username: 用户名
        email: 邮箱
        nickname: 昵称
        name: 姓名
        age: 年龄
        role_id: 主角色ID
        role_code: 角色编码
        status: 用户状态
        avatar_url: 头像URL
        last_login_at: 最后登录时间
    """

    id: int = Field(description="用户ID")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str | None = Field(default=None, description="姓名")
    age: int | None = Field(default=None, description="年龄")
    role_id: int | None = Field(default=None, description="主角色ID")
    role_code: str | None = Field(default=None, description="角色编码")
    status: str = Field(description="用户状态")
    avatar_url: str | None = Field(default=None, description="头像URL")
    last_login_at: datetime | None = Field(default=None, description="最后登录时间")

    model_config = ConfigDict(from_attributes=True)