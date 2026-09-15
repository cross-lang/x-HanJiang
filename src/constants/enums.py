#!/usr/bin/env python3
"""业务枚举定义。

集中定义项目通用枚举类型，供 schemas / services / repositories 复用。
枚举值对齐数据库列定义，避免业务代码中出现魔法字符串。
"""

from enum import Enum


class CommonStatus(Enum):
    """通用启用/停用状态（对齐 roles、permissions 等表的 status 列）。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


class UserStatus(Enum):
    """用户状态（对齐 users.status 列）。"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


class AlertChannel(Enum):
    """系统告警发送渠道。"""

    EMAIL = "email"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
