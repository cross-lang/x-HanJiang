#!/usr/bin/env python3
"""
通用枚举常量

本模块集中定义项目通用的枚举类型，供 services / schemas / repositories 复用。

Classes:
    CommonStatus: 通用启用/停用状态（对齐 roles/permissions 等表的 status 列）
    UserStatus: 用户状态（对齐 users.status ENUM）
"""

from enum import Enum


class CommonStatus(Enum):
    """通用启用/停用状态。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


class UserStatus(Enum):
    """用户状态枚举（对齐 users 表的 status 列）。"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
