#!/usr/bin/env python3
"""AI 助手业务常量与枚举。

集中定义 AI 助手模块的 SSE 事件类型、会话消息角色、工具标识与系统入口清单，
避免业务代码中出现魔法字符串。按规范禁止散落业务字符串，全部收拢至此。
"""

from src.constants.base import StrBaseEnum
from src.constants.permissions import PermissionCode

# ── AI 助手 SSE 事件类型 ────────────────────────────────


class AssistantEventType(StrBaseEnum):
    """AI 助手 SSE 流式事件类型（api 层透出给前端）。"""

    THINKING = ("thinking", "模型思考过程（可选透出）")
    TOKEN = ("token", "回复文本增量")
    NAVIGATE = ("navigate", "跳转指令（前端执行 router.push）")
    DENIED = ("denied", "越权拒绝提示")
    ERROR = ("error", "服务错误提示")
    DONE = ("done", "本轮回答结束")


# ── 会话消息角色 ─────────────────────────────────────────


class AssistantMessageRole(StrBaseEnum):
    """会话消息角色（对齐 assistant_messages.role 列）。
    注：工具调用过程消息不落库（避免回放时缺少 tool_call_id 导致非法），
    仅持久化 user / assistant 两类角色。
    """

    USER = ("user", "用户")
    ASSISTANT = ("assistant", "AI 助手")
    TOOL = ("tool", "工具结果")


# ── 工具标识 ─────────────────────────────────────────────

#: 跳转工具名称（作为 tool name 暴露给模型）
NAVIGATE_TOOL_NAME: str = "navigate"


# ── 权限元数据 ───────────────────────────────────────────

#: AI 助手对话 / 反馈权限码统一在 PermissionCode 中维护：
#: PermissionCode.ASSISTANT_CHAT / PermissionCode.ASSISTANT_FEEDBACK。
#: 对话接口不强制该权限，仅要求登录，权限码仅作元数据声明。


# ── 编排参数 ─────────────────────────────────────────────

#: 大模型服务不可用时的兜底回复（持久化到会话，避免前端空白）
ASSISTANT_FALLBACK_MESSAGE: str = "AI 助手服务暂时不可用，请稍后再试。"
#: 空回复兜底文案：模型未输出任何内容时展示，避免空白回复
ASSISTANT_EMPTY_REPLY_MESSAGE: str = "抱歉，我没能理解您的问题。请换个说法。"
#: 滚动摘要每次折入的旧消息条数（控制单次压缩成本）
ASSISTANT_ROLL_CHUNK_SIZE: int = 4
#: 滚动摘要触发系数：消息总数超过（保留轮数 × 2）时触发一次压缩
ASSISTANT_ROLL_TRIGGER_FACTOR: int = 2
#: 审计日志中的实体类型标识（AI 助手）
ASSISTANT_ENTITY_TYPE: str = "assistant"
#: 会话消息列表查询上限
ASSISTANT_MESSAGE_LIST_LIMIT: int = 100


# ── 系统入口清单（跳转工具的知识源）────────────────────────

#: 系统入口清单：page 标识 / 前端路径 / 标题 / 用途说明 / 所需权限码（空 = 登录即可访问）。
#: 权限码引用 PermissionCode 统一目录，与 api/v1 各业务路由的 @permission 声明一致；
#: 后续可替换为从菜单表（menu）动态生成，此处为 P0 静态清单。
ASSISTANT_ENTRY_CATALOG: tuple[dict[str, str], ...] = (
    {
        "page": "dashboard",
        "path": "/dashboard",
        "title": "首页",
        "description": "系统概览与核心指标看板",
        "permission": "",
    },
    {
        "page": "users",
        "path": "/users",
        "title": "用户管理",
        "description": "用户列表、新增、编辑与启用停用",
        "permission": PermissionCode.USER_VIEW.mark,
    },
    {
        "page": "roles",
        "path": "/roles",
        "title": "角色管理",
        "description": "角色创建、编辑与权限绑定",
        "permission": PermissionCode.ROLE_VIEW.mark,
    },
    {
        "page": "permissions",
        "path": "/permissions",
        "title": "权限管理",
        "description": "系统权限列表与说明",
        "permission": PermissionCode.PERMISSION_VIEW.mark,
    },
    {
        "page": "audit",
        "path": "/audit",
        "title": "审计日志",
        "description": "操作审计记录：操作人、实体类型、操作、备注与IP，支持导出CSV",
        "permission": PermissionCode.AUDIT_LOG_VIEW.mark,
    },
    {
        "page": "audit_login",
        "path": "/audit/login",
        "title": "登录日志",
        "description": "用户登录记录：用户名、姓名、登录方式、状态、IP与时间，支持导出CSV",
        "permission": PermissionCode.LOGIN_LOG_VIEW.mark,
    },
    {
        "page": "apps",
        "path": "/apps",
        "title": "开放平台应用",
        "description": "开放平台应用列表：新建、编辑、启用/禁用、重置密钥与删除（管理员分配应用）",
        "permission": PermissionCode.OPENAPI_APP_VIEW.mark,
    },
    {
        "page": "app-approvals",
        "path": "/app-approvals",
        "title": "应用审批",
        "description": "开发者提交的应用创建/修改申请审批：通过或驳回（驳回需填写原因）",
        "permission": PermissionCode.OPENAPI_APP_APPROVE.mark,
    },
    {
        "page": "developers",
        "path": "/open-developers",
        "title": "开发者管理",
        "description": "开放平台开发者列表查询，可查看开发者旗下应用",
        "permission": PermissionCode.OPENAPI_DEV_VIEW.mark,
    },
    {
        "page": "files",
        "path": "/files",
        "title": "文件管理",
        "description": "上传文件与文件列表管理",
        "permission": PermissionCode.FILE_VIEW.mark,
    },
    {
        "page": "station-messages",
        "path": "/station-messages",
        "title": "站内信",
        "description": "我的站内信：历史消息列表、按来源/接收日期/关键词过滤、查看详情、导出CSV",
        "permission": PermissionCode.STATION_VIEW.mark,
    },
    {
        "page": "profile",
        "path": "/profile",
        "title": "个人中心",
        "description": "个人资料、头像与通知偏好设置",
        "permission": "",
    },
)
