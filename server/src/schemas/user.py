#!/usr/bin/env python3
"""
用户数据模型

本模块定义用户管理相关的请求和响应数据传输对象（DTO）。

Classes:
    UserCreateRequest: 用户创建请求模型
    UserUpdateRequest: 用户更新请求模型
    UserResponse: 用户响应模型
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.constants.enums import UserStatus


class UserCreateRequest(BaseModel):
    """用户创建请求模型。

    Attributes:
        username: 用户名（3-50 位）
        email: 邮箱（全局唯一）
        password: 初始密码（8-64 位，服务端存储 bcrypt 哈希）
        phone: 手机号
        avatar_url: 头像URL
        role_id: 主角色ID
        status: 状态（active/inactive/locked）
    """

    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: str = Field(max_length=100, description="邮箱（全局唯一）")
    password: str = Field(default="ChangeMe@123", min_length=8, max_length=64, description="初始密码")
    name: str | None = Field(default=None, max_length=100, description="姓名")
    age: int | None = Field(default=None, ge=0, le=200, description="年龄")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    avatar_url: str | None = Field(default=None, max_length=500, description="头像URL")
    role_id: int | None = Field(default=None, description="主角色ID")
    role_name: str | None = Field(default=None, description="角色名称")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="状态")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """校验邮箱格式。"""
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式不正确")
        return v


class UserUpdateRequest(BaseModel):
    """用户更新请求模型。

    所有字段均为可选，仅更新提供的字段。

    Attributes:
        username: 用户名
        email: 邮箱
        password: 新密码（提供时重新哈希）
        phone: 手机号
        avatar_url: 头像URL
        role_id: 主角色ID
        status: 状态
    """

    username: str | None = Field(default=None, min_length=3, max_length=50, description="用户名")
    email: str | None = Field(default=None, max_length=100, description="邮箱")
    password: str | None = Field(default=None, min_length=8, max_length=64, description="新密码")
    name: str | None = Field(default=None, max_length=100, description="姓名")
    age: int | None = Field(default=None, ge=0, le=200, description="年龄")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    avatar_url: str | None = Field(default=None, max_length=500, description="头像URL")
    role_id: int | None = Field(default=None, description="主角色ID")
    role_name: str | None = Field(default=None, description="角色名称")
    status: UserStatus | None = Field(default=None, description="状态")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """校验邮箱格式（可选字段）。"""
        if v is None:
            return v
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式不正确")
        return v


class AdminResetPasswordRequest(BaseModel):
    """管理员重置密码请求模型。

    Attributes:
        new_password: 新密码
        confirm_password: 确认密码
    """

    new_password: str = Field(
        min_length=8,
        max_length=64,
        description="新密码（至少 8 位）",
    )
    confirm_password: str = Field(
        min_length=8,
        max_length=64,
        description="确认密码",
    )

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """用户响应模型（不含密码哈希）。

    Attributes:
        id: 用户唯一标识
        username: 用户名
        email: 邮箱
        phone: 手机号
        avatar_url: 头像URL
        role_id: 主角色ID
        status: 状态
        last_login_at: 最后登录时间
        last_login_ip: 最后登录IP
        created_at: 创建时间
        updated_at: 更新时间
    """

    id: int = Field(description="用户唯一标识")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str | None = Field(default=None, description="姓名")
    age: int | None = Field(default=None, description="年龄")
    phone: str | None = Field(default=None, description="手机号")
    avatar_url: str | None = Field(default=None, description="头像URL")
    role_id: int | None = Field(default=None, description="主角色ID")
    role_name: str | None = Field(default=None, description="角色名称")
    status: str = Field(description="状态")
    last_login_at: datetime | None = Field(default=None, description="最后登录时间")
    last_login_ip: str | None = Field(default=None, description="最后登录IP")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("last_login_at", "created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: object) -> datetime | None:
        """将 ISO 字符串解析为 datetime，便于前端处理。"""
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
