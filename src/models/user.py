#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据模型

本模块定义了用户相关的请求和响应数据传输对象（DTO），
作为项目三层架构的示例模型，展示标准的模型定义规范。

Classes:
    UserCreateRequest: 用户创建请求模型
    UserUpdateRequest: 用户更新请求模型
    UserResponse: 用户响应模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
