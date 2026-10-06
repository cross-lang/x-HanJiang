#!/usr/bin/env python3
"""业务枚举定义。

集中定义项目通用枚举类型，供 schemas / services / repositories 复用。
枚举值对齐数据库列定义，避免业务代码中出现魔法字符串。
按业务类别分组，以横线注释区分。
"""

from enum import Enum

from src.constants.base import IntBaseEnum, StrBaseEnum

# ── 运行环境域 ────────────────────────────────────────


class Environment(StrBaseEnum):
    """运行环境（对齐配置 app_env，可直接与裸字符串比较）。"""

    DEVELOPMENT = "development", "开发环境"
    TESTING = "testing", "测试环境"
    PRODUCTION = "production", "生产环境"


# ── 通用状态域 ────────────────────────────────────────


class CommonStatus(Enum):
    """通用启用/停用状态（对齐 roles、permissions 等表的 status 列）。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


# ── 用户域 ────────────────────────────────────────────


class UserStatus(StrBaseEnum):
    """用户状态（对齐 users.status 列：enabled 启用 / disabled 禁用）。"""

    ENABLED = "enabled", "启用"
    DISABLED = "disabled", "禁用"


class Gender(StrBaseEnum):
    """用户性别（对齐 users.gender 列：male 男 / female 女）。"""

    MALE = "male", "男"
    FEMALE = "female", "女"


# ── 角色权限域 ────────────────────────────────────────


class SystemRoleCode(StrBaseEnum):
    """系统内置角色编码（种子数据中固定存在，不可删除）。"""

    SUPERADMIN = ("superadmin", "超级管理员")
    ADMIN = ("admin", "管理员")
    USER = ("user", "普通用户")


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


class AppOwnerType(StrBaseEnum):
    """开放应用归属类型（对齐 openapi_apps.owner_type 列）。
    DEVELOPER：开发者门户自助创建（owner_id → developers.id）；
    ADMIN：    管理系统管理员分配/代建（owner_id → users.id）。
    """

    DEVELOPER = "developer", "开发者"
    ADMIN = "admin", "管理员"


class AppRegistrationType(StrBaseEnum):
    """开放应用申请类型（对齐 openapi_app_registrations.registration_type 列）。

    CREATE：创建应用申请（应用记录随申请一并创建，审批通过后 approved 置 True）；
    UPDATE：修改应用申请（基本信息 / scope 调整统一走该类型，审批通过后快照落地到应用表）。
    """

    CREATE = "create", "创建申请"
    UPDATE = "update", "修改申请"


class AppApprovalStatus(StrBaseEnum):
    """开放应用申请审批状态（对齐 openapi_app_registrations.status 列）。

    应用申请表 openapi_app_registrations 按批次记录每次创建/修改申请：
    开发者提交后为 pending，由管理员在管理系统审批通过（approved）或驳回（rejected）。
    """

    PENDING = "pending", "待审批"
    APPROVED = "approved", "已通过"
    REJECTED = "rejected", "已驳回"


# ── 开放平台开发者域 ────────────────────────────────────


class DeveloperStatus(StrBaseEnum):
    """开放平台开发者账号状态（对齐 developers.status 列）。"""

    ENABLED = "enabled", "启用"
    DISABLED = "disabled", "禁用"


class CertificationType(StrBaseEnum):
    """开发者认证类型（对齐 developers.certification_type 列）。"""

    PERSONAL = "personal", "个人认证"
    ENTERPRISE = "enterprise", "企业认证"


class CertificationStatus(StrBaseEnum):
    """开发者认证状态（对齐 developers.certification_status 列）。"""

    NONE = "none", "未认证"
    PENDING = "pending", "审批中"
    APPROVED = "approved", "已认证"
    REJECTED = "rejected", "已驳回"


class DeveloperMessageStatus(StrBaseEnum):
    """开发者站内信阅读状态（对齐 developer_messages.status 列）。

    开发者站内信与管理系统用户站内信（station_messages）分表，
    独立表 developer_messages 的状态取值沿用站内信惯例：unread / read。
    """

    UNREAD = "unread", "未读"
    READ = "read", "已读"


class DeveloperMessageCategory(StrBaseEnum):
    """开发者站内信类型（对齐 developer_messages.category 列）。

    与 web/open_portal 前端 OpenMessage.category 约定一致：
    system 系统消息 / audit 审批结果 / notify 业务通知。
    """

    SYSTEM = "system", "系统消息"
    AUDIT = "audit", "审批结果"
    NOTIFY = "notify", "业务通知"


# ── 通知域 ────────────────────────────────────────────


class NotificationChannel(StrBaseEnum):
    """通知发送渠道"""

    STATION = "station", "站内信"
    EMAIL = "email", "邮件"
    SMS = "sms", "短信"
    DINGTALK = "dingtalk", "钉钉"
    FEISHU = "feishu", "飞书"


class NotificationEvent(StrBaseEnum):
    """通知事件类型。
    按业务域分组，格式：{domain}.{action}
    走 dispatcher 的事件必须在 templates/notification_templates/ 下有对应模板；
    直接入库型事件（SYSTEM_NOTICE / STATION_MESSAGE）内容由调用方给出，无需模板。
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
    SYSTEM_NOTICE = "system.notice", "系统通知（发布/维护广播站内信）"
    # ── 站内信域 ────────────────────────────────
    STATION_MESSAGE = "station.message", "站内消息"
    # ── 文件域 ──────────────────────────────────
    FILE_UPLOADED = "file.uploaded", "文件上传完成"
    FILE_DELETED = "file.deleted", "文件已删除"
    FILE_DOWNLOADED = "file.downloaded", "文件被下载"


# 默认通知路由表：事件类型 → 默认发送渠道
# 未显式指定渠道的 dispatch 调用使用该路由表决定发送渠道。
DEFAULT_ROUTES: dict[NotificationEvent, list[NotificationChannel]] = {
    # 用户域
    NotificationEvent.USER_PASSWORD_CHANGED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL
    ],
    NotificationEvent.USER_PROFILE_UPDATED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL
    ],
    NotificationEvent.USER_STATUS_CHANGED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.USER_LOGIN_FAILED: [
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK
    ],
    NotificationEvent.USER_CREATED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL
    ],
    NotificationEvent.USER_DELETED: [
        NotificationChannel.EMAIL
    ],
    NotificationEvent.LOGIN_NEW_DEVICE: [
        NotificationChannel.EMAIL
    ],
    # 角色权限域
    NotificationEvent.ROLE_ASSIGNED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.PERMISSION_GRANTED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL
    ],
    NotificationEvent.PERMISSION_REVOKED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.ROLE_DELETED: [
        NotificationChannel.STATION
    ],
    # 文件域
    NotificationEvent.FILE_UPLOADED: [
        NotificationChannel.STATION
    ],
    NotificationEvent.FILE_DELETED: [
        NotificationChannel.STATION
    ],
    NotificationEvent.FILE_DOWNLOADED: [
        NotificationChannel.STATION
    ],
    # 开放应用域
    NotificationEvent.OPENAPI_APP_CREATED: [
        NotificationChannel.STATION
    ],
    NotificationEvent.OPENAPI_APP_UPDATED: [
        NotificationChannel.STATION
    ],
    NotificationEvent.OPENAPI_APP_DELETED: [
        NotificationChannel.STATION
    ],
    NotificationEvent.OPENAPI_APP_KEY_RESET: [
        NotificationChannel.EMAIL
    ],
    # 系统域
    NotificationEvent.SYSTEM_ALERT: [
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
        NotificationChannel.FEISHU,
    ],

    # 系统通知 / 站内信：直接入库型事件，仅走站内信；
    # 显式配置以防 dispatch 未传渠道时兜底误发邮件
    NotificationEvent.SYSTEM_NOTICE: [
        NotificationChannel.STATION
    ],
    NotificationEvent.STATION_MESSAGE: [
        NotificationChannel.STATION
    ],
}


class NotificationStatus(StrBaseEnum):
    """通知发送状态。"""

    PENDING = "pending", "待发送"
    SUCCESS = "success", "发送成功"
    FAILED = "failed", "发送失败"
    RETRYING = "retrying", "重试中"


class NotificationSource(StrBaseEnum):
    """通知投递来源（notifications_delivery.source / station_messages.source）。

    用于区分同一条投递/消息由哪个业务域产生：
    - system_notice: 系统通知广播（通知管理发布）
    - alert: 系统告警
    - openapi_app: 开放应用审批通知
    - manual: 手动触发（业务代码直接调用 dispatcher）
    station 站内信直发走独立 station_messages 表，不在本枚举里。
    """

    SYSTEM_NOTICE = "system_notice", "系统通知"
    ALERT = "alert", "系统告警"
    OPENAPI_APP = "openapi_app", "开放应用审批"
    MANUAL = "manual", "手动触发"


class SystemNotificationType(StrBaseEnum):
    """系统通知类型（决定发布语义与维护参数是否必填）。"""

    NOTICE = "notice", "普通通知"
    MAINTENANCE = "maintenance", "系统维护"


class SystemNotificationStatus(StrBaseEnum):
    """系统通知发布状态。"""

    PUBLISHED = "published", "已发布"
    WITHDRAWN = "withdrawn", "已撤回"


class NotificationTargetType(StrBaseEnum):
    """系统通知发布受众类型。"""

    ALL = "all", "全体用户"
    ROLES = "roles", "指定角色"
    USERS = "users", "指定用户"


class NotificationErrorCode(StrBaseEnum):
    """通知模块业务错误码（随异常 error_code 返回，前端据此做文案映射与分支处理）。"""

    NOTICE_NOT_FOUND = "notice_not_found", "通知不存在"
    NOTICE_ALREADY_WITHDRAWN = "notice_already_withdrawn", "通知已撤回"
    NOTICE_CANNOT_WITHDRAW = "notice_cannot_withdraw", "当前状态不可撤回"
    NOTICE_CANNOT_REPUBLISH = "notice_cannot_republish", "当前状态不可重新发布"
    TARGET_ROLES_NOT_FOUND = "target_roles_not_found", "目标角色不存在"
    TARGET_USERS_EMPTY = "target_users_empty", "目标用户为空"
    NO_ACTIVE_USERS = "no_active_users", "没有可推送的活跃用户"
    CHANNEL_TEST_FAILED = "channel_test_failed", "渠道测试发送失败"


# ── 公告域 ────────────────────────────────────────────


class AnnouncementContentType(StrBaseEnum):
    """公告正文格式类型。"""

    MARKDOWN = "markdown", "Markdown"
    RICHTEXT = "richtext", "富文本"


class AnnouncementPosition(StrBaseEnum):
    """公告展示位置（首页板块 / 横幅）。"""

    BOARD = "board", "首页板块"
    BANNER = "banner", "首页横幅"


class AnnouncementStatus(StrBaseEnum):
    """公告发布状态。"""

    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"
    UNPUBLISHED = "unpublished", "已下架"


# ── 日志域 ────────────────────────────────────────────


class LoginStatus(StrBaseEnum):
    """登录日志状态（对齐 login_logs.status 列）。"""

    SUCCESS = "success", "成功"
    FAILED = "failed", "失败"


class LoginType(StrBaseEnum):
    """登录方式（对齐 login_logs.login_type 列）。"""

    PASSWORD = "password", "密码"
    SSO = "sso", "单点登录"


class AuditAction(StrBaseEnum):
    """审计日志动作中"无权限码对应"的独有事件。

    重合的 CRUD / 文件 / 发布类动作统一使用
    :class:`src.constants.permissions.PermissionAction` 的 mark，本枚举只保留
    登录 / 登出 / 绑定权限等不对应任何权限码的审计事件。
    """

    LOGIN = "login", "登录"
    LOGOUT = "logout", "退出登录"
    BIND_PERMISSION = "bind_permission", "绑定权限"
    UNBIND_PERMISSION = "unbind_permission", "解绑权限"


# ── HTTP 域 ───────────────────────────────────────────

class HttpContentType(StrBaseEnum):
    """HTTP Content-Type 媒体类型枚举"""
    APPLICATION_JSON = "application/json", "JSON"
    APPLICATION_OCTET_STREAM = "application/octet-stream", "二进制流"
    APPLICATION_X_WWW_FORM_URLENCODED = "application/x-www-form-urlencoded", "表单数据编码"
    MULTIPART_FORM_DATA = "multipart/form-data", "多部分表单数据"
    TEXT_EVENT_STREAM = "text/event-stream", "事件流（SSE）"


class HttpHeaders(StrBaseEnum):
    """HTTP 请求头"""
    X_REQUEST_ID = "X-Request-ID", "请求ID"
    X_REAL_IP = "X-Real-IP", "真实地址"
    X_FORWARDED_FOR = "X-Forwarded-For", "转发地址"
    AUTHORIZATION = "Authorization", "认证头"
    CONTENT_TYPE = "Content-Type", "内容类型"
    ACCEPT = "Accept", "可接受类型"
    USER_AGENT = "User-Agent", "用户代理"


class HttpStatusCode(IntBaseEnum):
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


class ApiResponseCode(IntBaseEnum):
    """API 响应码"""
    SUCCESS = 0, "Success"
    ERROR = -1, "An error occurred"
    VALIDATION_ERROR = 40001, "Validation failed"
    UNAUTHORIZED = 40101, "Unauthorized"
    FORBIDDEN = 40301, "Forbidden"
    NOT_FOUND = 40401, "Resource not found"
    RATE_LIMIT_EXCEEDED = 42901, "Rate limit exceeded"
    SERVER_ERROR = 50001, "Internal server error"
    DATABASE_ERROR = 50002, "Database operation failed"
    EXTERNAL_SERVICE_ERROR = 50003, "External service call failed"
    DOCUMENT_ERROR = 50004, "Document processing failed"
    EMBEDDING_ERROR = 50005, "Embedding generation failed"
    VECTOR_STORE_ERROR = 50006, "Vector store operation failed"
    RETRIEVAL_ERROR = 50007, "Retrieval operation failed"
    GENERATION_ERROR = 50008, "Content generation failed"


class ApiResponseMessage(StrBaseEnum):
    """API 响应消息"""
    SUCCESS = "success", "成功"
    INTERNAL_ERROR = "Internal server error", "内部服务器错误"
    NOT_FOUND = "Resource not found", "资源不存在"
    VALIDATION_ERROR = "Validation error", "参数校验错误"
    AUTHENTICATION_FAILED = "Authentication failed", "认证失败"
    AUTHORIZATION_DENIED = "Permission denied", "权限拒绝"

