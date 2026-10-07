#!/usr/bin/env python3
"""管理端用户特有 DTO。

双渠道共享的用户管理模型（创建/更新/响应）位于 schemas/user.py；
本文件仅保留管理系统渠道特有的请求模型。
"""

from pydantic import BaseModel, ConfigDict, Field


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
