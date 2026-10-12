#!/usr/bin/env python3
"""
认证数据模型
本模块定义认证（登录/刷新令牌/当前用户）相关的请求和响应 DTO。

Classes:
    LoginRequest: 登录请求模型
    TokenResponse: 令牌响应模型
    RefreshTokenRequest: 刷新令牌请求模型
    CurrentUser: 当前用户信息响应模型
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """登录请求模型（RSA 加密传输）。
    支持用户名、手机号或邮箱登录；密码以 RSA-OAEP 密文提交，不再直传明文。

    Attributes:
        username: 用户名/手机号/邮箱
        encrypted_password: RSA 加密后的密码（密文 = nonce|timestamp|password）
        nonce: 一次性随机串（须来自 GET /auth/public-key 的下发值）
    """

    username: str = Field(min_length=3, max_length=100, description="用户名/手机号/邮箱")
    encrypted_password: str = Field(min_length=1, max_length=1024, description="RSA 加密后的密码")
    nonce: str = Field(min_length=1, max_length=64, description="一次性 nonce")
    model_config = ConfigDict(from_attributes=True)


class LoginPublicKeyResponse(BaseModel):
    """登录公钥响应模型（登录前先获取，用于前端加密密码）。

    Attributes:
        public_key: RSA 公钥 PEM（前端 JSEncrypt 加密用）
        nonce: 一次性随机串（登录时随密文提交，防重放）
        timestamp: 服务器 epoch 秒（前端原样拼进密文，用于时间窗校验）
        expires_in: nonce 有效期（秒）
    """

    public_key: str = Field(description="RSA 公钥 PEM")
    nonce: str = Field(description="一次性 nonce")
    timestamp: int = Field(description="服务器时间戳（epoch 秒）")
    expires_in: int = Field(description="nonce 有效期（秒）")
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


class CurrentUser(BaseModel):
    """当前用户信息响应模型。

    Attributes:
        id: 用户ID
        username: 用户名
        email: 邮箱
        name: 姓名
        role_code: 角色编码
        status: 用户状态
        avatar_url: 头像URL
        last_login_at: 最后登录时间
    """

    id: int = Field(description="用户ID")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str | None = Field(default=None, description="姓名")
    role_code: str | None = Field(default=None, description="角色编码")
    status: str = Field(description="用户状态")
    avatar_url: str | None = Field(default=None, description="头像URL")
    phone: str | None = Field(default=None, description="手机号")
    birthday: str | None = Field(default=None, description="生日")
    gender: str | None = Field(default=None, description="性别")
    last_login_at: datetime | None = Field(default=None, description="最后登录时间")
    permissions: list[str] = Field(default_factory=list, description="当前用户拥有的权限码列表")
    model_config = ConfigDict(from_attributes=True)
