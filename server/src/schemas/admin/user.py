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
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.constants.enums import UserStatus
from src.utils.time import normalize_date_str


class UserCreateRequest(BaseModel):
    """用户创建请求模型。

    Attributes:
        username: 用户名（3-50 位）
        email: 邮箱（全局唯一）
        password: 初始密码（8-64 位，服务端存储 bcrypt 哈希）
        phone: 手机号
        avatar_url: 头像URL
        role_ids: 角色ID列表（至少 1 个）
        status: 状态（active/inactive/locked）
    """

    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: str = Field(max_length=100, description="邮箱（全局唯一）")
    password: str = Field(min_length=8, max_length=64, description="初始密码")
    name: str = Field(max_length=100, description="姓名")
    phone: str = Field(max_length=20, description="手机号")
    gender: str = Field(min_length=1, description="性别（male/female）")
    birthday: str = Field(min_length=1, description="生日（YYYY-MM-DD）")
    avatar_url: str | None = Field(default=None, max_length=500, description="头像URL")
    role_ids: list[int] = Field(min_length=1, description="角色ID列表（至少 1 个）")
    role_name: str | None = Field(default=None, description="角色名称")
    roles: list[dict[str, Any]] = Field(default_factory=list, description="用户角色列表")
    status: UserStatus = Field(default=UserStatus.ENABLED, description="状态")
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """校验邮箱格式。"""
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("birthday", mode="before")
    @classmethod
    def parse_birthday(cls, v: object) -> str | None:
        """将 ISO datetime / date / datetime 输入规范化为本地日期 YYYY-MM-DD。

        带时区的 ISO 字符串按 Asia/Shanghai 本地时区换算，避免时区偏移导致日期差一天。

        Args:
            v: birthday 原始输入（前端可能传 ISO 格式如 2000-01-01T16:00:00.000Z）

        Returns:
            str | None: 归一化为 YYYY-MM-DD 的字符串；输入为 None 时返回 None

        Raises:
            ValueError: 无法识别的日期格式
        """
        return normalize_date_str(v)


class UserUpdateRequest(BaseModel):
    """用户更新请求模型。
    所有字段均为可选，仅更新提供的字段。

    Attributes:
        username: 用户名
        email: 邮箱
        password: 新密码（提供时重新哈希）
        phone: 手机号
        avatar_url: 头像URL
        role_ids: 角色ID列表
        status: 状态
    """

    username: str | None = Field(default=None, min_length=3, max_length=50, description="用户名")
    email: str | None = Field(default=None, max_length=100, description="邮箱")
    password: str | None = Field(default=None, min_length=8, max_length=64, description="新密码")
    name: str | None = Field(default=None, max_length=100, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    avatar_url: str | None = Field(default=None, max_length=500, description="头像URL")
    birthday: str | None = Field(default=None, description="生日（YYYY-MM-DD）")
    gender: str | None = Field(default=None, description="性别（male/female）")
    role_ids: list[int] | None = Field(default=None, description="角色ID列表")
    role_name: str | None = Field(default=None, description="角色名称")
    roles: list[dict[str, Any]] = Field(default_factory=list, description="用户角色列表")
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

    @field_validator("birthday", mode="before")
    @classmethod
    def parse_birthday(cls, v: object) -> str | None:
        """将 ISO datetime / date / datetime 输入规范化为本地日期 YYYY-MM-DD。

        带时区的 ISO 字符串按 Asia/Shanghai 本地时区换算，避免时区偏移导致日期差一天。

        Args:
            v: birthday 原始输入（前端可能传 ISO 格式如 2000-01-01T16:00:00.000Z）

        Returns:
            str | None: 归一化为 YYYY-MM-DD 的字符串；输入为 None 时返回 None

        Raises:
            ValueError: 无法识别的日期格式
        """
        return normalize_date_str(v)


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
        status: 状态
        last_login_at: 最后登录时间
        last_login_ip: 最后登录IP
        created_at: 创建时间
        updated_at: 更新时间
    """

    id: int = Field(description="用户唯一标识")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    name: str = Field(description="姓名")
    phone: str = Field(description="手机号")
    avatar_url: str | None = Field(default=None, description="头像URL")
    roles: list[dict[str, Any]] = Field(default_factory=list, description="用户角色列表")
    status: str = Field(description="状态")
    last_login_at: datetime | None = Field(default=None, description="最后登录时间")
    last_login_ip: str | None = Field(default=None, description="最后登录IP")
    gender: str = Field(description="性别（male/female）")
    birthday: str = Field(description="生日（YYYY-MM-DD）")

    @field_validator("birthday", mode="before")
    @classmethod
    def parse_birthday(cls, v: object) -> str | None:
        """将生日输入规范化为本地日期 YYYY-MM-DD（兼容 ISO datetime，时区换算避免差一天）。

        Args:
            v: birthday 原始输入（str / date / datetime / None）

        Returns:
            str | None: 归一化后的日期字符串

        Raises:
            ValueError: 无法识别的日期格式
        """
        return normalize_date_str(v)

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
