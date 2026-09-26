#!/usr/bin/env python3
"""
登录日志数据模型

本模块定义登录日志相关的响应数据传输对象（DTO）。

Classes:
    LoginLogResponse: 登录日志响应模型
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginLogResponse(BaseModel):
    """登录日志响应模型。"""

    id: int = Field(description="日志唯一标识")
    user_id: int | None = Field(default=None, description="用户ID")
    login_type: str = Field(description="登录方式（password/sso）")
    ip_address: str | None = Field(default=None, description="IP地址")
    status: str = Field(description="登录结果（success/failed）")
    created_at: datetime | None = Field(default=None, description="创建时间")

    model_config = ConfigDict(from_attributes=True)
