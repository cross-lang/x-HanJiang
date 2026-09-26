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


class PermissionCode(Enum):
    """权限编码集中定义。

    格式：{module}:{operation}
    所有 require_user_permission 调用必须引用本枚举，禁止散落字符串。
    种子数据从本枚举遍历生成。
    """

    # ── 用户管理 ──────────────────────────────
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    USER_EXPORT = "user:export"
    USER_IMPORT = "user:import"

    # ── 角色管理 ──────────────────────────────
    ROLE_VIEW = "role:view"
    ROLE_CREATE = "role:create"
    ROLE_EDIT = "role:edit"
    ROLE_DELETE = "role:delete"

    # ── 文件管理 ──────────────────────────────
    FILE_VIEW = "file:view"
    FILE_CREATE = "file:create"
    FILE_DELETE = "file:delete"

    # ── 审计日志 ──────────────────────────────
    AUDIT_VIEW = "audit:view"

    # ── 通知管理 ──────────────────────────────
    NOTIFICATION_VIEW = "notification:view"
    NOTIFICATION_CREATE = "notification:create"

    # ── 告警管理 ──────────────────────────────
    ALERT_BROADCAST = "alert:broadcast"

    # ── 维护管理 ──────────────────────────────
    MAINTENANCE_NOTIFY = "maintenance:notify"

    # ── 开放平台应用 ──────────────────────────
    OPENAPI_APP_VIEW = "openapi_app:view"
    OPENAPI_APP_CREATE = "openapi_app:create"
    OPENAPI_APP_EDIT = "openapi_app:edit"
    OPENAPI_APP_DELETE = "openapi_app:delete"
