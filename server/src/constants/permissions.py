#!/usr/bin/env python3
"""用户态系统权限码统一目录（权限元数据的唯一事实来源）。

权限的编码 / 中文名 / 所属模块 / 操作类型 / 描述 / 排序号全部在
PermissionCode 中定义一次；模块编码与中文名映射集中在 PermissionModule。
以下消费方均从本目录派生，禁止再硬编码权限码：
    - api 路由：@permission(PermissionCode.XXX) 挂载元数据，
      require_user_permission(PermissionCode.XXX.mark) 做鉴权
    - core/seed.py：初始化 permissions 表、绑定内置角色
    - 启动时路由扫描同步（collect_permissions_from_app）
    - 前端菜单种子、全局搜索分类映射、AI 助手入口清单

成员定义顺序即权限管理后台的展示顺序（sort_order 递增）。
无对应路由的权限（如 SWAGGER_VIEW）仍会写入
permissions 表并绑定给内置角色，但会被启动同步标记为 deprecated。
"""

from __future__ import annotations

from src.constants.base import StrBaseEnum, BaseEnum



class PermissionModule(StrBaseEnum):
    """用户态权限模块编码与中文名映射（与 PermissionCode.module 一一对应）。"""

    USER = ("user", "用户管理")
    ROLE = ("role", "角色管理")
    PERMISSION = ("permission", "权限管理")
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
    SEARCH = ("search", "全局搜索")
    ASSISTANT = ("assistant", "AI助手")


class PermissionCode(BaseEnum):
    """系统内置权限编码及元数据。

    成员值为 6 元组：
        (perm_code, perm_name, module, operation, description, sort_order)
    其中 mark（继承自 BaseEnum）即 perm_code，desc 即 perm_name，
    可直接与裸字符串比较（PermissionCode.X == "x:y"）。
    """

    def __init__(
        self,
        mark: str,
        perm_name: str,
        module: str,
        operation: str,
        description: str,
        sort_order: int,
    ) -> None:
        super().__init__(mark, perm_name)
        self._perm_name = perm_name
        self._module = module
        self._operation = operation
        self._description = description
        self._sort_order = sort_order

    @property
    def perm_name(self) -> str:
        """权限中文名。"""
        return self._perm_name

    @property
    def module(self) -> str:
        """所属模块编码。"""
        return self._module

    @property
    def operation(self) -> str:
        """操作类型。"""
        return self._operation

    @property
    def description(self) -> str:
        """权限描述。"""
        return self._description

    @property
    def sort_order(self) -> int:
        """展示排序号。"""
        return self._sort_order

    # ── 用户域 ────────────────────────────────────────────
    USER_VIEW = ("user:view", "查看用户", "user", "view", "查看用户列表与详情", 1)
    USER_CREATE = ("user:create", "创建用户", "user", "create", "创建新用户", 2)
    USER_EDIT = ("user:edit", "编辑用户", "user", "edit", "编辑用户信息", 3)
    USER_DELETE = ("user:delete", "删除用户", "user", "delete", "删除用户", 4)
    USER_EXPORT = ("user:export", "导出用户", "user", "export", "导出用户列表", 5)
    USER_IMPORT = ("user:import", "导入用户", "user", "import", "导入用户列表", 6)

    # ── 角色域 ────────────────────────────────────────────
    ROLE_VIEW = ("role:view", "查看角色", "role", "view", "查看角色列表与详情", 10)
    ROLE_CREATE = ("role:create", "创建角色", "role", "create", "创建新角色", 11)
    ROLE_EDIT = ("role:edit", "编辑角色", "role", "edit", "编辑角色信息", 12)
    ROLE_PERMISSION = ("role:permission", "分配角色权限", "role", "permission", "为角色绑定或解绑权限", 13)
    ROLE_DELETE = ("role:delete", "删除角色", "role", "delete", "删除角色", 14)

    # ── 权限定义域 ────────────────────────────────────────
    PERMISSION_VIEW = ("permission:view", "查看权限定义", "permission", "view", "查询权限定义列表与详情", 15)

    # ── 文件域 ────────────────────────────────────────────
    FILE_VIEW = ("file:view", "查看文件", "file", "view", "查看文件列表与详情", 20)
    FILE_CREATE = ("file:create", "上传文件", "file", "create", "上传文件", 21)
    FILE_DELETE = ("file:delete", "删除文件", "file", "delete", "删除文件", 22)

    # ── 日志域 ────────────────────────────────────────────
    AUDIT_LOG_VIEW = ("audit_log:view", "查看审计日志", "audit_log", "view", "查看业务审计日志", 30)
    AUDIT_LOG_EXPORT = ("audit_log:export", "导出审计日志", "audit_log", "export", "导出审计日志CSV", 31)
    LOGIN_LOG_VIEW = ("login_log:view", "查看登录日志", "login_log", "view", "查看登录日志", 35)
    LOGIN_LOG_EXPORT = ("login_log:export", "导出登录日志", "login_log", "export", "导出登录日志CSV", 36)

    # ── 通知 / 告警域 ─────────────────────────────────────
    NOTIFICATION_VIEW = ("notification:view", "查看通知", "notification", "view", "查看通知记录", 40)
    NOTIFICATION_CREATE = ("notification:create", "发布通知", "notification", "create", "发布系统通知", 41)
    NOTIFICATION_WITHDRAW = (
        "notification:withdraw", "撤回通知", "notification", "withdraw", "撤回已发布的系统通知", 42
    )
    ALERT_BROADCAST = ("alert:broadcast", "广播告警", "alert", "broadcast", "向全体用户广播告警", 50)
    ALERT_SEND = ("alert:send", "发送告警", "alert", "send", "向指定用户或全体用户发送告警", 50)
    NOTIFICATION_CONFIG = ("notification:config", "通知配置管理", "notification", "config", "系统通知渠道配置管理", 52)

    # ── 公告域 ────────────────────────────────────────────
    ANNOUNCEMENT_VIEW = ("announcement:view", "查看公告", "announcement", "view", "查看公告列表与详情", 53)
    ANNOUNCEMENT_CREATE = ("announcement:create", "创建公告", "announcement", "create", "创建新公告", 54)
    ANNOUNCEMENT_EDIT = ("announcement:edit", "编辑公告", "announcement", "edit", "编辑公告信息", 55)
    ANNOUNCEMENT_DELETE = ("announcement:delete", "删除公告", "announcement", "delete", "删除公告", 56)
    ANNOUNCEMENT_PUBLISH = ("announcement:publish", "发布公告", "announcement", "publish", "发布/下架公告", 57)

    # ── 开放平台域 ────────────────────────────────────────
    OPENAPI_APP_VIEW = ("openapi_app:view", "查看开放平台应用", "openapi_app", "view", "查看开放平台应用列表", 60)
    OPENAPI_APP_CREATE = ("openapi_app:create", "创建开放平台应用", "openapi_app", "create", "创建开放平台应用", 61)
    OPENAPI_APP_EDIT = ("openapi_app:edit", "编辑开放平台应用", "openapi_app", "edit", "编辑开放平台应用基本信息", 62)
    OPENAPI_APP_SCOPES = (
        "openapi_app:scopes", "配置应用权限范围", "openapi_app", "scopes", "更新开放应用的权限范围(scope)", 63
    )
    OPENAPI_APP_STATUS = (
        "openapi_app:status", "启停开放平台应用", "openapi_app", "status", "启用或禁用开放平台应用", 64
    )
    OPENAPI_APP_ROTATE_KEY = (
        "openapi_app:rotate_key", "重置开放应用AppKey", "openapi_app", "rotate_key", "重置应用密钥，旧密钥立即失效", 65
    )
    OPENAPI_APP_DELETE = ("openapi_app:delete", "删除开放平台应用", "openapi_app", "delete", "删除开放平台应用", 66)
    OPENAPI_SCOPE_VIEW = (
        "openapi_scope:view", "查看开放平台权限", "openapi_scope", "view", "查看开放平台 scope 列表", 67
    )

    # ── 仪表盘域 ────────────────────────────────────────
    DASHBOARD_VIEW = ("dashboard:view", "查看仪表盘", "dashboard", "view", "获取仪表盘关键指标", 70)

    # ── 个人中心域 ────────────────────────────────────────
    PROFILE_VIEW = ("profile:view", "查看个人中心", "profile", "view", "查看个人资料与通知设置", 71)
    PROFILE_EDIT = ("profile:edit", "编辑个人中心", "profile", "edit", "修改个人资料与通知设置", 72)
    PROFILE_PASSWORD = ("profile:password", "修改密码", "profile", "password", "修改个人登录密码", 73)
    PROFILE_EMAIL = ("profile:email", "更换邮箱", "profile", "email", "通过验证码二次认证更换登录邮箱", 74)
    PROFILE_PHONE = ("profile:phone", "更换手机号", "profile", "phone", "通过验证码二次认证更换手机号", 75)

    # ── 站内信域 ────────────────────────────────────────
    STATION_VIEW = ("station:view", "查看站内信", "station", "view", "查看站内信列表与未读数", 76)
    STATION_EDIT = ("station:edit", "管理站内信", "station", "edit", "标记站内信已读", 77)

    # ── 全局搜索域 ────────────────────────────────────────
    SEARCH = ("search:search", "全局搜索", "search", "search", "跨模块关键字搜索", 78)

    # ── 接口文档域 ────────────────────────────────────────
    SWAGGER_VIEW = ("swagger:view", "查看Swagger文档", "swagger", "view", "查看API Swagger文档", 80)

    # ── AI 助手域 ─────────────────────────────────────────
    ASSISTANT_CHAT = ("assistant:chat", "AI助手对话", "assistant", "chat", "与AI助手对话", 90)
    ASSISTANT_CONVERSATION = (
        "assistant:conversation", "AI助手会话管理", "assistant", "conversation", "创建、查询、删除或置顶会话", 91
    )
    ASSISTANT_FEEDBACK = ("assistant:feedback", "AI助手反馈", "assistant", "feedback", "对话消息反馈", 92)


#: 权限目录（成员定义顺序），供种子初始化等批量场景遍历
PERMISSION_CATALOG: tuple[PermissionCode, ...] = tuple(PermissionCode)


__all__ = ["PermissionCode", "PERMISSION_CATALOG"]
