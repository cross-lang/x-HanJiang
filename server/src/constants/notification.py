#!/usr/bin/env python3
"""通知与站内信常量/枚举。

集中定义通知域（发送渠道、事件、状态、来源、受众、错误码）以及
通知/广播相关常量，供 schemas / services / repositories 复用。
枚举值对齐数据库列定义，避免业务代码中出现魔法字符串。
按业务类别分组，以横线注释区分。
"""

from src.constants.base import StrBaseEnum

# ── 通知渠道域 ────────────────────────────────────────


class NotificationChannel(StrBaseEnum):
    """通知发送渠道"""

    STATION = "station", "站内信"
    EMAIL = "email", "邮件"
    SMS = "sms", "短信"
    DINGTALK = "dingtalk", "钉钉"
    FEISHU = "feishu", "飞书"


# 个人通知偏好矩阵可订阅的渠道白名单。
# sms 当前仅承担验证码直发（无个人短信接收方绑定入口、通知短信签名模板未接入），
# 个人事件短信通道接入后再将其纳入白名单。
PERSONAL_SUBSCRIBABLE_CHANNELS: frozenset[NotificationChannel] = frozenset(
    {
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
        NotificationChannel.FEISHU,
    }
)


# ── 通知事件域 ────────────────────────────────────────


class NotificationEvent(StrBaseEnum):
    """通知事件类型。
    按业务域分组，格式：{domain}.{action}
    走 dispatcher 的事件必须在 src/templates/notification_templates/ 下有对应模板；
    直接入库型事件（SYSTEM_NOTICE / STATION_MESSAGE）内容由调用方给出，无需模板。
    """

    # ── 用户域 ──────────────────────────────────
    USER_PASSWORD_CHANGED = "user.password_changed", "密码修改"
    USER_PROFILE_UPDATED = "user.profile_updated", "资料变更"
    USER_ENABLED = "user.enabled", "用户启用"
    USER_DISABLED = "user.disabled", "用户禁用"
    USER_LOGIN_FAILED = "user.login_failed", "连续登录失败告警"
    USER_CREATED = "user.created", "新用户创建"
    USER_DELETED = "user.deleted", "用户已删除"
    LOGIN_NEW_DEVICE = "login.new_device", "新设备登录"
    # ── 开放应用域 ──────────────────────────────────
    OPENAPI_APP_CREATED = "openapi_app.created", "开放应用已创建"
    OPENAPI_APP_UPDATED = "openapi_app.updated", "开放应用已更新"
    OPENAPI_APP_DELETED = "openapi_app.deleted", "开放应用已删除"
    OPENAPI_APP_KEY_RESET = "openapi_app.key_reset", "AppKey已重置"
    OPENAPI_APP_REGISTRATION = "openapi_app_registration", "开放应用审批"
    # ── 开发者域 ──────────────────────────────────
    # 开发者与管理系统用户分表平行（无 user_id 关联），本域事件仅投递操作者回执；
    # 开发者本人感知走门户站内信（developers 站内信表），不经订阅矩阵
    DEVELOPER_ENABLED = "developer.enabled", "开发者启用"
    DEVELOPER_DISABLED = "developer.disabled", "开发者禁用"
    DEVELOPER_DELETED = "developer.deleted", "开发者删除"
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
    # ── 安全域 ──────────────────────────────────
    SECURITY_VERIFY_CODE = "security.verify_code", "邮箱验证码"


# 个人通知偏好矩阵可订阅的事件白名单。
# 不在此列的事件不进矩阵、不接受个人订阅：
# - SYSTEM_ALERT 走系统监控渠道（系统级 webhook/邮件组），与个人订阅无关
# - SYSTEM_NOTICE / STATION_MESSAGE 为直传内容或直写入库型通知
# - SECURITY_VERIFY_CODE 为验证码直发邮件，无订阅语义
# - FILE_UPLOADED / FILE_DOWNLOADED / OPENAPI_APP_KEY_RESET 为预留事件（业务触发点未实现）
PERSONAL_SUBSCRIBABLE_EVENTS: frozenset[NotificationEvent] = frozenset(
    {
        NotificationEvent.USER_PASSWORD_CHANGED,
        NotificationEvent.USER_PROFILE_UPDATED,
        NotificationEvent.USER_ENABLED,
        NotificationEvent.USER_DISABLED,
        NotificationEvent.USER_LOGIN_FAILED,
        NotificationEvent.USER_CREATED,
        NotificationEvent.USER_DELETED,
        NotificationEvent.LOGIN_NEW_DEVICE,
        NotificationEvent.OPENAPI_APP_CREATED,
        NotificationEvent.OPENAPI_APP_UPDATED,
        NotificationEvent.OPENAPI_APP_DELETED,
        NotificationEvent.OPENAPI_APP_REGISTRATION,
        NotificationEvent.DEVELOPER_ENABLED,
        NotificationEvent.DEVELOPER_DISABLED,
        NotificationEvent.DEVELOPER_DELETED,
        NotificationEvent.ROLE_ASSIGNED,
        NotificationEvent.ROLE_DELETED,
        NotificationEvent.PERMISSION_GRANTED,
        NotificationEvent.PERMISSION_REVOKED,
        NotificationEvent.FILE_DELETED,
    }
)


# 默认通知路由表：事件类型 → 默认发送渠道
# 未显式指定渠道的 dispatch 调用使用该路由表决定发送渠道。
DEFAULT_ROUTES: dict[NotificationEvent, list[NotificationChannel]] = {
    # 用户域
    NotificationEvent.USER_PASSWORD_CHANGED: [NotificationChannel.STATION, NotificationChannel.EMAIL],
    NotificationEvent.USER_PROFILE_UPDATED: [NotificationChannel.STATION, NotificationChannel.EMAIL],
    NotificationEvent.USER_ENABLED: [
        NotificationChannel.STATION,
        NotificationChannel.EMAIL,
        NotificationChannel.DINGTALK,
    ],
    NotificationEvent.USER_DISABLED: [
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
    # 安全域
    NotificationEvent.SECURITY_VERIFY_CODE: [NotificationChannel.EMAIL],
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
    # 系统通知 / 站内信：直接入库型事件，仅走站内信；
    # 显式配置以防 dispatch 未传渠道时兜底误发邮件
    NotificationEvent.SYSTEM_NOTICE: [NotificationChannel.STATION],
    NotificationEvent.STATION_MESSAGE: [NotificationChannel.STATION],
}


# ── 通知状态域 ────────────────────────────────────────


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


# ── 系统通知域 ────────────────────────────────────────


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


# ── 通知与广播常量 ────────────────────────────────────
DEFAULT_ENABLED_CHANNEL: str = "station"  # 用户通知偏好未显式配置时的默认启用渠道（站内信默认开启）
MAX_BROADCAST_USER_LIMIT: int = 10000  # 告警/维护广播单次查询用户上限
# 验证码邮件事件类型（与 NotificationEvent.SECURITY_VERIFY_CODE 对齐）
VERIFY_CODE_EVENT: str = NotificationEvent.SECURITY_VERIFY_CODE.mark
