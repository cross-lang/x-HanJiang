#!/usr/bin/env python3
"""通用全局常量。

集中定义应用信息、环境标识、请求上下文键、响应消息、
用户字段约束等全局常量。禁止在业务代码中硬编码这些值。
按业务类别分组，以横线注释区分。
"""

# ── 应用信息 ──────────────────────────────────────────
APP_ID: str = "x-HanJiang"
APP_NAME: str = "汉江（HanJiang）"
APP_DESCRIPTION: str = "一个基于 FastAPI 框架深度封装的生产级 Python Web 应用框架"
APP_VERSION: str = "0.1.0"

# ── API 路由 ──────────────────────────────────────────
# 基础前缀；具体版本号（/v1）由各路由组在自己的 router 上声明，
# 例如：用户态 /api/v1，开放平台 /api/open/v1。
API_PREFIX: str = "/api"
OPEN_API_PREFIX: str = "/api/open"

# ── 环境标识 ──────────────────────────────────────────
ENV_DEVELOPMENT: str = "development"
ENV_TESTING: str = "testing"
ENV_PRODUCTION: str = "production"

# ── 配置文件 ──────────────────────────────────────────
DEFAULT_CONFIG_DIR: str = "."
DEFAULT_CONFIG_FILE: str = "config.yaml"

# ── 请求上下文 ────────────────────────────────────────
REQUEST_ID_HEADER: str = "X-Request-ID"  # 请求头中的 Request ID 字段名
CONTEXT_REQUEST_ID: str = "request_id"  # request.state 中的键
CONTEXT_REAL_IP: str = "real_ip"  # request.state 中的键

# ── 开放平台鉴权 ──────────────────────────────────────
# plain 模式：X-App-Id + X-App-Key
# hmac 模式：X-App-Id + X-App-Date + X-App-Authorization
OPENAPI_HEADER_APP_ID: str = "X-App-Id"
OPENAPI_HEADER_APP_KEY: str = "X-App-Key"
OPENAPI_HEADER_DATE: str = "X-App-Date"
OPENAPI_HEADER_AUTHORIZATION: str = "X-App-Authorization"
OPENAPI_ALGORITHM: str = "HanJiang-1"
OPENAPI_SIGNATURE_WINDOW_SECONDS: int = 300
# 签名串中 Content-Type 固定值（协议约定：固定 application/json，
# 与请求是否携带 body 无关；GET 无 body 时签名串同样拼接该值）
OPENAPI_CONTENT_TYPE: str = "application/json"

# ── 账号与令牌 ────────────────────────────────────────
# 超级管理员用户名（种子数据固定，业务代码中禁止硬编码 "superadmin"）
SUPERADMIN_USERNAME: str = "superadmin"

# 用户名长度约束
USERNAME_MIN_LENGTH: int = 3
USERNAME_MAX_LENGTH: int = 50

# 登录态 / 访问令牌有效期（秒）＝ 7 天；与配置 auth.access_token_expire_minutes 对齐
TOKEN_TTL_SECONDS: int = 60 * 60 * 24 * 7

# ── 菜单 ──────────────────────────────────────────────
MENU_STATUS_ENABLED: str = "enabled"  # 菜单启用状态
MENU_TYPE_DIRECTORY: str = "directory"  # 目录型菜单（无 children 时不可见）
MENU_ROOT_PARENT_ID: int = 0  # 根菜单的父 ID（0=根）

# ── 个人中心：邮箱二次认证验证码 ──────────────────────
VERIFY_CODE_TTL_SECONDS: int = 300  # 验证码有效期（5 分钟）
VERIFY_CODE_MIN: int = 100000  # 验证码随机范围下界（含）
VERIFY_CODE_MAX: int = 999999  # 验证码随机范围上界（含）
VERIFY_CODE_CACHE_PREFIX: str = "verify_code:"  # 验证码 Redis Key 前缀
VERIFY_CODE_EVENT: str = "security.verify_code"  # 验证码邮件事件类型

# ── 通知与广播 ────────────────────────────────────────
DEFAULT_ENABLED_CHANNEL: str = "station"  # 用户通知偏好未显式配置时的默认启用渠道（站内信默认开启）
NOTIFICATION_EVENT_STATION_MESSAGE: str = "station.message"  # 站内信专用事件类型
SYSTEM_NOTICE_EVENT: str = "system.notice"  # 系统通知（发布/维护广播）站内信事件类型
MAX_BROADCAST_USER_LIMIT: int = 10000  # 告警/维护广播单次查询用户上限

# ── 登录日志 ──────────────────────────────────────────
LOGIN_STATUS_SUCCESS: str = "success"  # 登录成功
LOGIN_STATUS_FAILED: str = "failed"  # 登录失败
LOGIN_STATUS_CN: dict[str, str] = {
    "success": "成功",
    "failed": "失败",
}
LOGIN_TYPE_CN: dict[str, str] = {
    "password": "密码登录",
    "sso": "单点登录",
}

# ── 审计日志 ──────────────────────────────────────────
AUDIT_ACTION_CN: dict[str, str] = {
    "create": "新增",
    "update": "更新",
    "delete": "删除",
    "bind_permission": "绑定权限",
    "unbind_permission": "解绑权限",
    "login": "登录",
    "logout": "退出登录",
    "export": "导出",
    "upload": "上传",
    "download": "下载",
    "publish": "发布",
    "unpublish": "下架",
    "withdraw": "撤回",
    "reset_password": "重置密码",
}

# ── 响应消息 ──────────────────────────────────────────
MSG_SUCCESS: str = "success"
MSG_INTERNAL_ERROR: str = "Internal server error"
MSG_NOT_FOUND: str = "Resource not found"
MSG_VALIDATION_ERROR: str = "Validation error"
MSG_AUTHENTICATION_FAILED: str = "Authentication failed"
MSG_AUTHORIZATION_DENIED: str = "Permission denied"
