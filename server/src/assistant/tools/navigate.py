#!/usr/bin/env python3
"""跳转工具：引导用户进入系统指定入口。"""

from __future__ import annotations

from typing import ClassVar

from src.assistant.tools.base import BaseTool, ToolArgs, ToolResult
from src.constants.assistant import (
    ASSISTANT_ENTRY_CATALOG,
    NAVIGATE_TOOL_NAME,
    AssistantEventType,
)
from src.core.logger import logger
from src.schemas.admin.auth import CurrentUser


class NavigateTool(BaseTool):
    """跳转工具：引导用户进入系统指定入口。

    权限规则：系统入口路由表中 permission 为空的页面登录即可访问；
    否则要求当前用户拥有对应权限码（或 * 超管通配）。
    """

    name = NAVIGATE_TOOL_NAME
    description = "跳转到管理系统的指定页面，只能选择当前用户有权限访问的入口"
    skill = "guide"
    parameters: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "page": {
                "type": "string",
                "enum": [item["page"] for item in ASSISTANT_ENTRY_CATALOG],
                "description": "目标页面标识",
            }
        },
        "required": ["page"],
    }

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        page = str(args.get("page", ""))
        entry: dict[str, str] | None = next(
            (item for item in ASSISTANT_ENTRY_CATALOG if item["page"] == page),
            None,
        )
        if entry is None:
            return ToolResult(content="未知页面标识，请只从系统系统入口路由表中选择页面")
        if not self._has_access(entry["permission"], user):
            logger.warning(f"AI 助手跳转被拒：user={user.id} page={page}")
            return ToolResult(
                content="当前用户无权访问该页面，请推荐其他入口",
                event_type=AssistantEventType.DENIED,
            )
        return ToolResult(
            content=(
                f"跳转成功：已引导用户进入「{entry['title']}」页面。"
                "请用一句简洁的话向用户确认已跳转到该页面，不要虚构或介绍该页面之外的信息。"
            ),
            event_type=AssistantEventType.NAVIGATE,
            event_data={"path": entry["path"]},
        )
