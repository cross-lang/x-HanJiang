#!/usr/bin/env python3
"""
用户模块常量定义

本模块定义了用户相关的业务常量和状态枚举。

Attributes:
    USERNAME_MIN_LENGTH: 用户名最小长度
    USERNAME_MAX_LENGTH: 用户名最大长度
    USER_STATUS_VALUES: 用户状态合法值集合
"""

from enum import Enum


# ============================================================
# 用户字段约束
# ============================================================
USERNAME_MIN_LENGTH: int = 3
USERNAME_MAX_LENGTH: int = 50


# ============================================================
# 用户状态枚举（对齐 users.status ENUM）
# ============================================================
class UserStatus(Enum):
    """用户状态枚举（对齐 users 表的 status 列）。"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
