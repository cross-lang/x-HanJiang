#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户模块常量定义

本模块定义了用户相关的业务常量和状态枚举。

Attributes:
    USERNAME_MIN_LENGTH: 用户名最小长度
    USERNAME_MAX_LENGTH: 用户名最大长度
    NAME_MIN_LENGTH: 显示名称最小长度
    NAME_MAX_LENGTH: 显示名称最大长度
    AGE_MIN: 最小年龄
    AGE_MAX: 最大年龄
"""

# ============================================================
# 用户字段约束
# ============================================================
USERNAME_MIN_LENGTH: int = 3
USERNAME_MAX_LENGTH: int = 50
NAME_MIN_LENGTH: int = 1
NAME_MAX_LENGTH: int = 100
AGE_MIN: int = 0
AGE_MAX: int = 150

# ============================================================
# 用户状态枚举
# ============================================================
from enum import Enum


class UserStatus(Enum):
    """用户状态枚举。

    Attributes:
        ACTIVE: 活跃状态
        INACTIVE: 非活跃状态
        DELETED: 已删除状态
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"