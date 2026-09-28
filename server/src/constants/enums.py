#!/usr/bin/env python3
"""业务枚举定义。

集中定义项目通用枚举类型，供 schemas / services / repositories 复用。
枚举值对齐数据库列定义，避免业务代码中出现魔法字符串。
按业务类别分组，以横线注释区分。
"""

from enum import Enum

from src.constants.base import BaseEnum

# ── 通用状态域 ────────────────────────────────────────


class CommonStatus(Enum):
    """通用启用/停用状态（对齐 roles、permissions 等表的 status 列）。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


# ── 用户域 ────────────────────────────────────────────


class UserStatus(Enum):
    """用户状态（对齐 users.status 列：enabled 启用 / disabled 禁用）。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


# ── 角色权限域 ────────────────────────────────────────


class SystemRoleCode(BaseEnum):
    """系统内置角色编码（种子数据中固定存在，不可删除）。"""

    SUPERADMIN = ("superadmin", "超级管理员")
    ADMIN = ("admin", "管理员")
    USER = ("user", "普通用户")


class ApiModuleCode(BaseEnum):
    """用户态权限模块编码与中文名映射。"""

    USER = ("user", "用户管理")
    ROLE = ("role", "角色管理")
    FILE = ("file", "文件管理")
    AUDIT_LOG = ("audit_log", "审计日志")
    LOGIN_LOG = ("login_log", "登录日志")
    NOTIFICATION = ("notification", "通知管理")
    ANNOUNCEMENT = ("announcement", "公告管理")
    ALERT = ("alert", "告警管理")
    MAINTENANCE = ("maintenance", "维护管理")
    OPENAPI_APP = ("openapi_app", "开放平台应用")
    OPENAPI_SCOPE = ("openapi_scope", "开放平台权限")
    DASHBOARD = ("dashboard", "仪表盘")
    SWAGGER = ("swagger", "接口文档")
    PROFILE = ("profile", "个人中心")
    STATION = ("station", "站内信")
    GLOBAL_SEARCH = ("global_search", "全局搜索")


# ── 开放平台域 ────────────────────────────────────────


class AppStatus(Enum):
    """开放平台应用状态（对齐 api_apps.status 列）。"""

    ACTIVE = "active"
    DISABLED = "disabled"


class AppAuthMode(Enum):
    """开放平台应用鉴权模式（对齐 api_apps.auth_mode 列）。
    PLAIN：仅接受 X-App-Key 明文比对；
    HMAC：  仅接受 HMAC 签名（timestamp + nonce + signature）；
    BOTH：  两种都接受（灰度迁移期用）。
    """

    PLAIN = "plain"
    HMAC = "hmac"
    BOTH = "both"


class OpenApiModuleCode(BaseEnum):
    """开放平台 scope 模块编码与中文名映射。"""

    USER = ("user", "用户管理")
    HEALTH = ("health", "健康检查")


# ── 通知域 ────────────────────────────────────────────


class NotificationChannel(BaseEnum):
    """通知发送渠道"""

    STATION = "station", "站内信"
    EMAIL = "email", "邮件"
    SMS = "sms", "短信"
    DINGTALK = "dingtalk", "钉钉"
    FEISHU = "feishu", "飞书"


class NotificationEvent(BaseEnum):
    """通知事件类型。
    按业务域分组，格式：{domain}.{action}
    所有事件类型必须在 templates/notification_templates/ 下有对应模板。
    """

    # ── 用户域 ──────────────────────────────────
    USER_PASSWORD_CHANGED = "user.password_changed", "密码修改"
    USER_PROFILE_UPDATED = "user.profile_updated", "资料变更"
    USER_STATUS_CHANGED = "user.status_changed", "账号状态变更"
    USER_LOGIN_FAILED = "user.login_failed", "连续登录失败告警"
    USER_CREATED = "user.created", "新用户创建"
    USER_DELETED = "user.deleted", "用户已删除"
    LOGIN_NEW_DEVICE = "login.new_device", "新设备登录"
    # ── 开放应用域 ──────────────────────────────────
    OPENAPI_APP_CREATED = "openapi_app.created", "开放应用已创建"
    OPENAPI_APP_UPDATED = "openapi_app.updated", "开放应用已更新"
    OPENAPI_APP_DELETED = "openapi_app.deleted", "开放应用已删除"
    OPENAPI_APP_KEY_RESET = "openapi_app.key_reset", "AppKey已重置"
    # ── 角色权限域 ──────────────────────────────
    ROLE_ASSIGNED = "role.assigned", "角色变更"
    ROLE_DELETED = "role.deleted", "角色已删除"
    PERMISSION_GRANTED = "permission.granted", "权限授予"
    PERMISSION_REVOKED = "permission.revoked", "权限回收"
    # ── 系统域 ──────────────────────────────────
    SYSTEM_ALERT = "system.alert", "系统告警"
    SYSTEM_MAINTENANCE = "system.maintenance", "系统维护通知"
    # ── 文件域 ──────────────────────────────────
    FILE_UPLOADED = "file.uploaded", "文件上传完成"
    FILE_DELETED = "file.deleted", "文件已删除"
    FILE_DOWNLOADED = "file.downloaded", "文件被下载"


# 默认通知路由表：事件类型 → 默认发送渠道
# 未显式指定渠道的 dispatch 调用使用该路由表决定发送渠道。
DEFAULT_ROUTES: dict[NotificationEvent, list[NotificationChannel]] = {
    # 用户域
    NotificationEvent.USER_PASSWORD_CHANGED: [NotificationChannel.STATION, NotificationChannel.EMAIL],
    NotificationEvent.USER_PROFILE_UPDATED: [NotificationChannel.STATION, NotificationChannel.EMAIL],
    NotificationEvent.USER_STATUS_CHANGED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.USER_LOGIN_FAILED: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK],
    NotificationEvent.USER_CREATED: [NotificationChannel.STATION, NotificationChannel.EMAIL],
    NotificationEvent.USER_DELETED: [NotificationChannel.EMAIL],
    NotificationEvent.LOGIN_NEW_DEVICE: [NotificationChannel.EMAIL],
    # 角色权限域
    NotificationEvent.ROLE_ASSIGNED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.PERMISSION_GRANTED: [NotificationChannel.STATION, NotificationChannel.EMAIL],
    NotificationEvent.PERMISSION_REVOKED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.ROLE_DELETED: [NotificationChannel.STATION],
    # 文件域
    NotificationEvent.FILE_UPLOADED: [NotificationChannel.STATION],
    NotificationEvent.FILE_DELETED: [NotificationChannel.STATION],
    NotificationEvent.FILE_DOWNLOADED: [NotificationChannel.STATION],
    # 开放应用域
    NotificationEvent.OPENAPI_APP_CREATED: [NotificationChannel.STATION],
    NotificationEvent.OPENAPI_APP_UPDATED: [NotificationChannel.STATION],
    NotificationEvent.OPENAPI_APP_DELETED: [NotificationChannel.STATION],
    NotificationEvent.OPENAPI_APP_KEY_RESET: [NotificationChannel.EMAIL],
    # 系统域
    NotificationEvent.SYSTEM_ALERT: [
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
        NotificationChannel.FEISHU,
    ],
    NotificationEvent.SYSTEM_MAINTENANCE: [
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
        NotificationChannel.FEISHU,
    ],
}


class NotificationStatus(BaseEnum):
    """通知发送状态。"""

    PENDING = "pending", "待发送"
    SUCCESS = "success", "发送成功"
    FAILED = "failed", "发送失败"
    RETRYING = "retrying", "重试中"


class StationMessageStatus(BaseEnum):
    """站内信阅读状态（对齐 notification_records.status 列的站内信取值）。"""

    UNREAD = "unread", "未读"
    READ = "read", "已读"


class SystemNotificationType(BaseEnum):
    """系统通知类型（决定发布语义与维护参数是否必填）。"""

    NOTICE = "notice", "普通通知"
    MAINTENANCE = "maintenance", "系统维护"


class SystemNotificationStatus(BaseEnum):
    """系统通知发布状态。"""

    PUBLISHED = "published", "已发布"
    WITHDRAWN = "withdrawn", "已撤回"


# ── 公告域 ────────────────────────────────────────────


class AnnouncementContentType(BaseEnum):
    """公告正文格式类型。"""

    MARKDOWN = "markdown", "Markdown"
    RICHTEXT = "richtext", "富文本"


class AnnouncementPosition(BaseEnum):
    """公告展示位置（首页板块 / 横幅）。"""

    BOARD = "board", "首页板块"
    BANNER = "banner", "首页横幅"


class AnnouncementStatus(BaseEnum):
    """公告发布状态。"""

    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"
    UNPUBLISHED = "unpublished", "已下架"


# ── HTTP 域 ───────────────────────────────────────────


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
