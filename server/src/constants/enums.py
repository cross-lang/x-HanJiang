#!/usr/bin/env python3
"""业务枚举定义。

集中定义项目通用枚举类型，供 schemas / services / repositories 复用。
枚举值对齐数据库列定义，避免业务代码中出现魔法字符串。
"""

from enum import Enum
from src.constants.base import BaseEnum

class CommonStatus(Enum):
    """通用启用/停用状态（对齐 roles、permissions 等表的 status 列）。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


class UserStatus(Enum):
    """用户状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


class AppAuthMode(Enum):
    """开放平台应用鉴权模式（对齐 api_apps.auth_mode 列）。

    PLAIN：仅接受 X-App-Key 明文比对；
    HMAC：  仅接受 HMAC 签名（timestamp + nonce + signature）；
    BOTH：  两种都接受（灰度迁移期用）。
    """

    PLAIN = "plain"
    HMAC = "hmac"
    BOTH = "both"


class NotificationChannel(BaseEnum):
    """通知发送渠道"""

    EMAIL = "email", "邮件"
    SMS = "sms", "短信"
    DINGTALK = "dingtalk", "钉钉"
    FEISHU = "feishu", "飞书"


class NotificationEvent(BaseEnum):
    """通知事件类型。

    按业务域分组，格式：{domain}.{action}
    所有事件类型必须在 config/notification_templates/ 下有对应模板。
    """

    # ── 用户域 ──────────────────────────────────
    USER_PASSWORD_CHANGED = "user.password_changed", "密码修改"
    USER_PROFILE_UPDATED = "user.profile_updated", "资料变更"
    USER_STATUS_CHANGED = "user.status_changed", "账号状态变更"
    USER_LOGIN_FAILED = "user.login_failed", "连续登录失败告警"

    # ── 角色权限域 ──────────────────────────────
    ROLE_ASSIGNED = "role.assigned", "角色变更"
    PERMISSION_GRANTED = "permission.granted", "权限授予"
    PERMISSION_REVOKED = "permission.revoked", "权限回收"

    # ── 系统域 ──────────────────────────────────
    SYSTEM_ALERT = "system.alert", "系统告警"
    SYSTEM_MAINTENANCE = "system.maintenance", "系统维护通知"


class NotificationStatus(BaseEnum):
    """通知发送状态。"""

    PENDING = "pending", "待发送"
    SUCCESS = "success", "发送成功"
    FAILED = "failed", "发送失败"
    RETRYING = "retrying", "重试中"


class HttpStatus(BaseEnum):
    """HTTP 状态码"""

    OK = 200, "OK"
    CREATED = 201, "Created"
    ACCEPTED = 202, "Accepted"
    NO_CONTENT = 204, "No Content"

    BAD_REQUEST = 400, "Bad Request"
    UNAUTHORIZED = 401, "Unauthorized"
    FORBIDDEN = 403, "Forbidden"
    NOT_FOUND = 404, "Not Found"
    METHOD_NOT_ALLOWED = 405, "Method Not Allowed"
    CONFLICT = 409, "Conflict"
    UNPROCESSABLE_ENTITY = 422, "Unprocessable Entity"
    TOO_MANY_REQUESTS = 429, "Too Many Requests"

    INTERNAL_SERVER_ERROR = 500, "Internal Server Error"
    NOT_IMPLEMENTED = 501, "Not Implemented"
    BAD_GATEWAY = 502, "Bad Gateway"
    SERVICE_UNAVAILABLE = 503, "Service Unavailable"
    GATEWAY_TIMEOUT = 504, "Gateway Timeout"


class HttpMediaType(Enum):
    """HTTP 内容类型（Content-Type）。"""

    JSON = "application/json"
    FILE = "application/octet-stream"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"




class ModuleCode(BaseEnum):
    """权限模块编码与中文名映射。"""

    USER = ("user", "用户管理")
    ROLE = ("role", "角色管理")
    FILE = ("file", "文件管理")
    AUDIT_LOG = ("audit_log", "审计日志")
    LOGIN_LOG = ("login_log", "登录日志")
    NOTIFICATION = ("notification", "通知管理")
    ALERT = ("alert", "告警管理")
    MAINTENANCE = ("maintenance", "维护管理")
    OPENAPI_APP = ("openapi_app", "开放平台应用")
