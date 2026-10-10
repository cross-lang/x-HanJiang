#!/usr/bin/env python3
"""tools 子包单测：只读查询工具的鉴权、脱敏与格式化输出。

用内存 fake 仓储替换真实数据库（与记忆层单测同思路），覆盖：
    - 无权限调用被拒绝（user:view / dashboard:view / openapi_app:view）
    - 正常路径的文本格式（Markdown 列表 + 状态中文 + 时间格式化）
    - 空结果 / 缺参提示
    - BuiltinToolSource 注册全部内置工具
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from src.assistant.tools import (
    BuiltinToolSource,
    QueryAnnouncementsTool,
    QueryAppStatusTool,
    QueryMyPermissionsTool,
    QuerySystemStatsTool,
    QueryUserInfoTool,
    ToolRegistry,
)
from src.constants.assistant import NAVIGATE_TOOL_NAME
from src.schemas.admin.auth import CurrentUser


def _make_user(permissions: list[str]) -> CurrentUser:
    """构造测试用当前用户。

    Args:
        permissions: 权限码列表（"*" 表示超管通配）

    Returns:
        CurrentUser: 最小合法用户对象
    """
    return CurrentUser(
        id=1,
        username="tester",
        email="tester@example.com",
        name="测试用户",
        status="enabled",
        permissions=permissions,
    )


# ── 仓储替身（仅实现各工具实际调用的方法） ─────────────────


class _FakeUser:
    """UserEntity 形状的最小替身（仅含工具输出所需字段）。"""

    def __init__(
        self,
        id: int,
        username: str,
        name: str,
        email: str,
        status: str,
        last_login_at: datetime | None,
    ) -> None:
        self.id = id
        self.username = username
        self.name = name
        self.email = email
        self.status = status
        self.last_login_at = last_login_at


class _FakeRole:
    """RoleEntity 形状的最小替身。"""

    def __init__(self, role_name: str) -> None:
        self.role_name = role_name


class _FakeAnnouncement:
    """AnnouncementEntity 形状的最小替身。"""

    def __init__(self, title: str, content: str, created_at: datetime) -> None:
        self.title = title
        self.content = content
        self.created_at = created_at


class _FakeApp:
    """OpenApiAppEntity 形状的最小替身（不含密钥字段）。"""

    def __init__(self, name: str, app_id: str, status: str, last_used_at: datetime | None) -> None:
        self.name = name
        self.app_id = app_id
        self.status = status
        self.last_used_at = last_used_at


class FakeUserRepository:
    """用户仓储替身：search + get_roles_by_user_id。"""

    def __init__(self, users: tuple[Any, ...] = (), roles_by_user: dict[int, list[_FakeRole]] | None = None) -> None:
        self._users = list(users)
        self._roles = roles_by_user or {}

    def search(self, keyword: str | None = None, status: str | None = None, skip: int = 0, limit: int = 100):
        return list(self._users), len(self._users)

    def get_roles_by_user_id(self, user_id: int) -> list[_FakeRole]:
        return list(self._roles.get(user_id, []))


class FakeDashboardRepository:
    """仪表盘仓储替身：card_counts / today_login_count / openapi_developer_count。"""

    def card_counts(self) -> tuple[int, int, int]:
        return (12, 3, 5)

    def today_login_count(self, day: Any) -> int:
        return 42

    def openapi_developer_count(self) -> int:
        return 7


class FakeAnnouncementRepository:
    """公告仓储替身：list_available。"""

    def __init__(self, rows: tuple[_FakeAnnouncement, ...] = ()) -> None:
        self._rows = list(rows)

    def list_available(self, position: str | None = None, limit: int = 20):
        return list(self._rows)[:limit]


class FakeOpenApiAppRepository:
    """开放平台应用仓储替身：search_by_keyword。"""

    def __init__(self, apps: tuple[_FakeApp, ...] = ()) -> None:
        self._apps = list(apps)

    def search_by_keyword(
        self,
        keyword: str | None = None,
        owner_type: str | None = None,
        owner_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return list(self._apps), len(self._apps)


# ── query_my_permissions：登录即可，权限码映射中文名 ─────────


class TestQueryMyPermissionsTool:
    def test_lists_codes_with_chinese_names(self):
        tool = QueryMyPermissionsTool()
        result = tool.execute({}, _make_user(["user:view", "custom:unknown"]))
        assert "user:view（查看用户）" in result.content
        assert "custom:unknown" in result.content  # 未知权限码原样保留
        assert "tester" in result.content

    def test_empty_permissions(self):
        tool = QueryMyPermissionsTool()
        result = tool.execute({}, _make_user([]))
        assert "（无）" in result.content


# ── query_user_info：需 user:view ────────────────────────────


class TestQueryUserInfoTool:
    def test_denied_without_permission(self):
        tool = QueryUserInfoTool(FakeUserRepository())
        result = tool.execute({"keyword": "tom"}, _make_user([]))
        assert "无权" in result.content

    def test_formats_users_with_roles(self):
        repo = FakeUserRepository(
            users=(_FakeUser(9, "tom", "汤姆", "tom@x.com", "enabled", datetime(2026, 1, 2, 3, 4)),),
            roles_by_user={9: [_FakeRole("管理员")]},
        )
        tool = QueryUserInfoTool(repo)
        result = tool.execute({"keyword": "tom"}, _make_user(["user:view"]))
        assert "tom（汤姆）" in result.content
        assert "启用" in result.content
        assert "管理员" in result.content
        assert "2026-01-02 03:04" in result.content

    def test_empty_result(self):
        tool = QueryUserInfoTool(FakeUserRepository())
        result = tool.execute({"keyword": "nobody"}, _make_user(["user:view"]))
        assert "未找到" in result.content

    def test_missing_keyword(self):
        tool = QueryUserInfoTool(FakeUserRepository())
        result = tool.execute({}, _make_user(["user:view"]))
        assert "关键字" in result.content


# ── query_system_stats：需 dashboard:view ────────────────────


class TestQuerySystemStatsTool:
    def test_denied_without_permission(self):
        tool = QuerySystemStatsTool(FakeDashboardRepository())
        result = tool.execute({}, _make_user([]))
        assert "无权" in result.content

    def test_formats_counts(self):
        tool = QuerySystemStatsTool(FakeDashboardRepository())
        result = tool.execute({}, _make_user(["dashboard:view"]))
        assert "12" in result.content
        assert "42" in result.content
        assert "7" in result.content


# ── query_announcements：全员可见（无权限码） ────────────────


class TestQueryAnnouncementsTool:
    def test_accessible_without_permission(self):
        repo = FakeAnnouncementRepository(
            (
                _FakeAnnouncement(
                    "系统维护通知", "本周六 02:00-04:00 系统维护\n请提前保存工作。", datetime(2026, 1, 1, 8, 0)
                ),
            )
        )
        result = QueryAnnouncementsTool(repo).execute({}, _make_user([]))
        assert "系统维护通知" in result.content
        assert "2026-01-01 08:00" in result.content
        # 正文换行折叠为单行摘要
        assert "本周六 02:00-04:00 系统维护 请提前保存工作。" in result.content

    def test_empty(self):
        result = QueryAnnouncementsTool(FakeAnnouncementRepository()).execute({}, _make_user([]))
        assert "没有生效" in result.content


# ── query_app_status：需 openapi_app:view，输出不含密钥 ──────


class TestQueryAppStatusTool:
    def test_denied_without_permission(self):
        tool = QueryAppStatusTool(FakeOpenApiAppRepository())
        result = tool.execute({"keyword": "直播"}, _make_user([]))
        assert "无权" in result.content

    def test_formats_apps(self):
        apps = (_FakeApp("直播平台", "hj_live_abc", "active", datetime(2026, 2, 3, 4, 5)),)
        tool = QueryAppStatusTool(FakeOpenApiAppRepository(apps))
        result = tool.execute({"keyword": "直播"}, _make_user(["openapi_app:view"]))
        assert "hj_live_abc" in result.content
        assert "启用" in result.content
        assert "2026-02-03 04:05" in result.content

    def test_empty_with_keyword(self):
        tool = QueryAppStatusTool(FakeOpenApiAppRepository())
        result = tool.execute({"keyword": "不存在的应用"}, _make_user(["openapi_app:view"]))
        assert "未找到" in result.content


# ── BuiltinToolSource：注册全部内置工具 ──────────────────────


class TestBuiltinToolSource:
    def test_registers_all_builtin_tools(self):
        registry = ToolRegistry()
        registry.register_source(BuiltinToolSource(session=MagicMock()))
        assert set(registry.names()) == {
            NAVIGATE_TOOL_NAME,
            "query_system_stats",
            "query_user_info",
            "query_my_permissions",
            "query_announcements",
            "query_app_status",
        }

    def test_schemas_exposed_to_model(self):
        registry = ToolRegistry()
        registry.register_source(BuiltinToolSource(session=MagicMock()))
        schemas = registry.schemas()
        assert len(schemas) == 6
        assert all(item["type"] == "function" for item in schemas)
