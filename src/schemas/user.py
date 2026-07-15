#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据模型

本模块定义了用户相关的请求和响应数据传输对象（DTO），
用于 API 层的数据校验和序列化。

Classes:
    UserCreateRequest: 用户创建请求模型
    UserUpdateRequest: 用户更新请求模型
    UserResponse: 用户响应模型
"""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreateRequest(BaseModel):
    """用户创建请求模型。

    Attributes:
        username: 用户名（唯一，3-50 个字符）
        email: 邮箱地址
        name: 显示名称
        age: 年龄（可选）
    """

    username: str = Field(
        min_length=3,
        max_length=50,
        description="用户名（唯一，3-50 个字符）",
    )
    email: str = Field(description="邮箱地址")
    name: str = Field(min_length=1, max_length=100, description="显示名称")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="年龄")

    model_config = ConfigDict(from_attributes=True)

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
        email: 邮箱地址
        name: 显示名称
        age: 年龄
    """

    email: Optional[str] = Field(default=None, description="邮箱地址")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="显示名称")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="年龄")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """校验邮箱格式（可选字段）。"""
        if v is None:
            return v
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式不正确")
        return v


class UserResponse(BaseModel):
    """用户响应模型。

    Attributes:
        id: 用户唯一标识
        username: 用户名
        email: 邮箱地址
        name: 显示名称
        age: 年龄
        created_at: 创建时间
    """

    id: int = Field(description="用户唯一标识")
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱地址")
    name: str = Field(description="显示名称")
    age: Optional[int] = Field(default=None, description="年龄")
    created_at: str = Field(default="", description="创建时间")

    model_config = ConfigDict(from_attributes=True)