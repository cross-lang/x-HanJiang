#!/usr/bin/env python3
"""工具注册表：统一 schema 导出与按名分发。"""

from __future__ import annotations

from src.assistant.tools.base import BaseTool, ToolArgs, ToolResult
from src.assistant.tools.sources import ToolSource
from src.core.logger import logger
from src.schemas.admin.auth import CurrentUser


class ToolRegistry:
    """工具注册表。

    支持运行时动态注册 / 注销工具，聚合内置与外部工具来源，
    统一生成 tools 声明并提供按名分发能力。
    """

    def __init__(self) -> None:
        """初始化空注册表。"""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具（同名工具将被覆盖）。

        Args:
            tool: 工具实例
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """注销一个工具（不存在时静默忽略）。

        Args:
            name: 工具名称
        """
        self._tools.pop(name, None)

    def register_source(self, source: ToolSource) -> None:
        """批量注册一个工具来源下的全部工具。

        Args:
            source: 工具来源实例
        """
        for tool in source.load_tools():
            self.register(tool)

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具。

        Args:
            name: 工具名称

        Returns:
            BaseTool | None: 工具实例，未注册时返回 None
        """
        return self._tools.get(name)

    def names(self) -> list[str]:
        """获取全部已注册工具名（按注册顺序）。

        Returns:
            list[str]: 工具名称列表
        """
        return list(self._tools.keys())

    def schemas(self) -> list[dict[str, object]]:
        """生成传给模型的全部工具声明。

        Returns:
            list[dict[str, object]]: tools 参数列表
        """
        return [tool.schema() for tool in self._tools.values()]

    def dispatch(self, name: str, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """按名称分发工具调用。

        未知工具一律拒绝并返回友好提示，不执行任何动作。

        Args:
            name: 工具名称
            args: 工具入参
            user: 当前用户

        Returns:
            ToolResult: 执行结果
        """
        tool = self._tools.get(name)
        if tool is None:
            logger.warning(f"AI 助手收到未知工具调用: {name}")
            return ToolResult(content="未知工具调用，已忽略")
        return tool.execute(args, user)
