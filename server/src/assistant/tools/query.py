#!/usr/bin/env python3
"""AI 助手只读查询工具（数据查询类，不产生任何写操作）。

设计约定：
    - 只读：全部工具仅调用仓储查询方法，无 create / update / delete
    - 鉴权：在 execute 内做后端校验（不信任模型 / 前端声明），权限码
      复用 PermissionCode（user:view / dashboard:view / openapi_app:view）；
      查自己的信息（query_my_permissions）与全员可见数据（生效中公告）
      登录即可查询
    - 脱敏：输出文本不含密码哈希、应用密钥明文、手机号等敏感字段
    - 数据依赖：仓储经构造函数注入（BuiltinToolSource 按请求组装），
      单测用内存 fake 替换即可，无需连库

工具清单：
    - query_system_stats      系统概况统计（活跃用户/角色/应用/今日登录/开发者数）
    - query_user_info         按用户名或邮箱关键字查询用户基础信息（需 user:view）
    - query_my_permissions    查询当前用户自己的角色与权限码（登录即可）
    - query_announcements     查询当前生效中的公告（全员可见，与首页横幅同源）
    - query_app_status        按名称关键字查询开放平台应用状态（需 openapi_app:view）
"""

from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

from src.assistant.tools.base import BaseTool, ToolArgs, ToolResult
from src.constants.assistant import (
    QUERY_ANNOUNCEMENTS_TOOL_NAME,
    QUERY_APP_STATUS_TOOL_NAME,
    QUERY_MY_PERMISSIONS_TOOL_NAME,
    QUERY_SYSTEM_STATS_TOOL_NAME,
    QUERY_USER_INFO_TOOL_NAME,
)
from src.constants.enums import AppStatus, UserStatus
from src.constants.permissions import PermissionCode
from src.repositories.announcement_repository import AnnouncementRepository
from src.repositories.dashboard_repository import DashboardRepository
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.repositories.user_repository import UserRepository
from src.schemas.admin.auth import CurrentUser

#: 用户/应用列表单次最多展示条数（控制回填给模型的文本长度）
_QUERY_LIMIT: int = 5
#: 生效中公告单次最多展示条数
_ANNOUNCEMENT_LIMIT: int = 10

#: 用户状态值 → 中文描述（取自 UserStatus 枚举元数据）
_USER_STATUS_DESC: dict[str, str] = {member.value: member.desc for member in UserStatus}
#: 应用状态值 → 中文描述（AppStatus 为纯值枚举，无中文元数据，此处对齐管理端口径）
_APP_STATUS_DESC: dict[str, str] = {
    AppStatus.ACTIVE.value: "启用",
    AppStatus.DISABLED.value: "停用",
}


def _format_dt(value: datetime | None, empty: str = "无") -> str:
    """格式化时间戳为「YYYY-MM-DD HH:MM」；空值返回占位文案。

    Args:
        value: 待格式化时间（可空）
        empty: 空值占位文案

    Returns:
        str: 格式化结果
    """
    if value is None:
        return empty
    return value.strftime("%Y-%m-%d %H:%M")


def _preview(text: str, limit: int = 50) -> str:
    """压缩公告正文为单行摘要（换行折叠 + 超长截断），控制回填文本长度。

    Args:
        text: 公告正文原文
        limit: 最大字符数

    Returns:
        str: 单行摘要（超长以「…」结尾）
    """
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[:limit]}…"


class QuerySystemStatsTool(BaseTool):
    """系统概况统计工具（复用仪表盘只读聚合查询，需 dashboard:view 权限）。"""

    name = QUERY_SYSTEM_STATS_TOOL_NAME
    description = (
        "查询系统概况统计：活跃用户数、启用角色数、活跃应用数、今日登录次数、开发者账号数"
    )
    skill = "data"
    parameters: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, dashboard_repository: DashboardRepository) -> None:
        """初始化系统统计工具。

        Args:
            dashboard_repository: 仪表盘统计仓储（只读聚合查询）
        """
        self._repository = dashboard_repository

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """统计系统概况指标并组织为 Markdown 列表文本。

        Args:
            args: 工具入参（本工具无参数）
            user: 当前用户（鉴权用）

        Returns:
            ToolResult: 统计文本；无权限时返回提示文本
        """
        if not self._has_access(PermissionCode.DASHBOARD_VIEW.value, user):
            return ToolResult(
                content=f"当前用户无权查看系统统计（需要「{PermissionCode.DASHBOARD_VIEW.perm_name}」权限），请向用户说明。"
            )
        user_count, role_count, app_count = self._repository.card_counts()
        today_login = self._repository.today_login_count(date.today())
        developer_count = self._repository.openapi_developer_count()
        lines = [
            f"- 活跃用户数：{user_count}",
            f"- 启用角色数：{role_count}",
            f"- 活跃应用数：{app_count}",
            f"- 今日登录次数：{today_login}",
            f"- 开发者账号数：{developer_count}",
        ]
        return ToolResult(content="系统概况统计：\n" + "\n".join(lines))


class QueryUserInfoTool(BaseTool):
    """用户信息查询工具（按用户名或邮箱关键字检索，需 user:view 权限）。

    脱敏：仅输出用户名 / 姓名 / 邮箱 / 状态 / 角色 / 最近登录时间，
    不含密码哈希、手机号等敏感字段。
    """

    name = QUERY_USER_INFO_TOOL_NAME
    description = "按用户名或邮箱关键字查询系统用户（返回基础信息与角色，不含敏感字段）"
    skill = "data"
    parameters: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "用户名或邮箱的包含匹配关键字",
            }
        },
        "required": ["keyword"],
    }

    def __init__(self, user_repository: UserRepository) -> None:
        """初始化用户查询工具。

        Args:
            user_repository: 用户仓储（关键字检索 + 角色关联查询）
        """
        self._repository = user_repository

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """检索用户并组织为 Markdown 列表文本。

        Args:
            args: 工具入参（keyword 必填）
            user: 当前用户（鉴权用）

        Returns:
            ToolResult: 查询结果文本；无权限 / 缺参 / 未命中时返回提示文本
        """
        if not self._has_access(PermissionCode.USER_VIEW.value, user):
            return ToolResult(
                content=f"当前用户无权查询用户信息（需要「{PermissionCode.USER_VIEW.perm_name}」权限），请向用户说明。"
            )
        keyword = str(args.get("keyword", "")).strip()
        if not keyword:
            return ToolResult(content="请提供要查询的用户名或邮箱关键字")
        users, total = self._repository.search(keyword=keyword, limit=_QUERY_LIMIT)
        if not users:
            return ToolResult(content=f"未找到用户名或邮箱包含「{keyword}」的用户")
        lines = []
        for entity in users:
            roles = [role.role_name for role in self._repository.get_roles_by_user_id(entity.id)]
            display_name = entity.name or entity.username
            lines.append(
                f"- {entity.username}（{display_name}）："
                f"状态{_USER_STATUS_DESC.get(entity.status, entity.status)}，"
                f"邮箱 {entity.email}，"
                f"角色 {'、'.join(roles) if roles else '无'}，"
                f"最近登录 {_format_dt(entity.last_login_at, '从未登录')}"
            )
        scope = f"共匹配 {total} 个用户" + (f"（最多展示 {_QUERY_LIMIT} 个）" if total > _QUERY_LIMIT else "")
        return ToolResult(content=f"用户查询结果（关键字「{keyword}」），{scope}：\n" + "\n".join(lines))


class QueryMyPermissionsTool(BaseTool):
    """我的权限查询工具（登录即可，查当前用户自己的角色与权限码）。"""

    name = QUERY_MY_PERMISSIONS_TOOL_NAME
    description = "查询当前对话用户自己的角色与权限码列表（无需权限，任何人可查自己）"
    skill = "guide"
    parameters: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """将当前用户的权限码映射为中文名列表（未知码原样保留）。

        Args:
            args: 工具入参（本工具无参数）
            user: 当前用户（数据来源，无需鉴权——查自己）

        Returns:
            ToolResult: 角色 + 权限码清单文本
        """
        name_map = {member.value: member.perm_name for member in PermissionCode}
        lines = [
            f"- {code}（{name_map[code]}）" if code in name_map else f"- {code}"
            for code in user.permissions
        ]
        perm_block = "\n".join(lines) if lines else "（无）"
        return ToolResult(
            content=(
                f"当前用户：{user.username}（{user.name or '未命名'}），角色：{user.role_code or '无'}\n"
                f"权限码共 {len(user.permissions)} 个：\n{perm_block}"
            )
        )


class QueryAnnouncementsTool(BaseTool):
    """生效中公告查询工具（全员可见，与首页横幅同源数据，无需权限码）。"""

    name = QUERY_ANNOUNCEMENTS_TOOL_NAME
    description = "查询当前生效中的系统公告（已发布且处于有效期内，含正文摘要）"
    skill = "data"
    parameters: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, announcement_repository: AnnouncementRepository) -> None:
        """初始化公告查询工具。

        Args:
            announcement_repository: 公告仓储（生效中公告查询）
        """
        self._repository = announcement_repository

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """查询生效中公告并组织为 Markdown 列表文本（含正文单行摘要）。

        Args:
            args: 工具入参（本工具无参数）
            user: 当前用户（未用——公告对登录用户全员可见）

        Returns:
            ToolResult: 公告列表文本；无生效公告时返回提示文本
        """
        rows = self._repository.list_available(limit=_ANNOUNCEMENT_LIMIT)
        if not rows:
            return ToolResult(content="当前没有生效中的公告")
        lines = [
            f"- {entity.title}（{_format_dt(entity.created_at, '未知时间')}发布）：{_preview(entity.content)}"
            for entity in rows
        ]
        return ToolResult(content="当前生效中的公告：\n" + "\n".join(lines))


class QueryAppStatusTool(BaseTool):
    """开放平台应用状态查询工具（需 openapi_app:view 权限）。

    脱敏：仅输出应用名 / app_id（明文对外标识）/ 状态 / 最近使用时间，
    不含密钥明文等机密字段。
    """

    name = QUERY_APP_STATUS_TOOL_NAME
    description = "按名称关键字查询开放平台应用的状态信息（应用名/状态/最近使用时间，不含密钥）"
    skill = "data"
    parameters: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "应用名称的包含匹配关键字（可选，缺省返回全部应用）",
            }
        },
        "required": [],
    }

    def __init__(self, openapi_app_repository: OpenApiAppRepository) -> None:
        """初始化应用状态查询工具。

        Args:
            openapi_app_repository: 开放平台应用仓储（关键字检索）
        """
        self._repository = openapi_app_repository

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """检索应用并组织为 Markdown 列表文本（不含密钥字段）。

        Args:
            args: 工具入参（keyword 可选）
            user: 当前用户（鉴权用）

        Returns:
            ToolResult: 应用列表文本；无权限 / 未命中时返回提示文本
        """
        if not self._has_access(PermissionCode.OPENAPI_APP_VIEW.value, user):
            return ToolResult(
                content=f"当前用户无权查询开放平台应用（需要「{PermissionCode.OPENAPI_APP_VIEW.perm_name}」权限），请向用户说明。"
            )
        keyword = str(args.get("keyword", "")).strip() or None
        apps, total = self._repository.search_by_keyword(keyword=keyword, limit=_QUERY_LIMIT)
        if not apps:
            if keyword:
                return ToolResult(content=f"未找到名称包含「{keyword}」的开放平台应用")
            return ToolResult(content="当前没有开放平台应用")
        lines = [
            f"- {entity.name}（app_id={entity.app_id}）："
            f"状态{_APP_STATUS_DESC.get(entity.status, entity.status)}，"
            f"最近使用 {_format_dt(entity.last_used_at, '从未')}"
            for entity in apps
        ]
        scope = f"共匹配 {total} 个应用" + (f"（最多展示 {_QUERY_LIMIT} 个）" if total > _QUERY_LIMIT else "")
        return ToolResult(content="开放平台应用查询结果，" + scope + "：\n" + "\n".join(lines))
