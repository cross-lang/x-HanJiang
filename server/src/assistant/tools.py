#!/usr/bin/env python3
"""AI 助手工具注册机制（"skill" 的落地）。

设计目标：
    - 工具采用注册机制：ToolRegistry 支持运行时动态注册 / 注销，
      后续新增工具只需实现 BaseTool 子类并 register，无需改动编排层
    - 工具来源可插拔：ToolSource 抽象聚合内置工具（BuiltinToolSource），
      预留 MCP 等外部来源（MCPToolSource，受配置开关控制）
    - 权限校验在工具执行内完成（后端校验，不信任模型 / 前端声明）

扩展约定：
    新增一个工具 = 继承 BaseTool + 在任意 ToolSource 中返回 + 注册进 Registry。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from src.constants.assistant import (
    ASSISTANT_ENTRY_CATALOG,
    NAVIGATE_TOOL_NAME,
    AssistantEventType,
)
from src.core.logger import logger
from src.schemas.admin.auth import CurrentUser

# 工具入参字典：key 为参数名，value 为 JSON 解析后的基础类型值
ToolArgs = dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """工具执行结果（回填给模型 + 可选透出前端的动作）。

    Attributes:
        content: 回填给模型的文本内容
        event_type: 需要透出前端的动作类型（可空）
        event_data: 动作附加数据（如跳转路径）
    """

    content: str
    event_type: AssistantEventType | None = None
    event_data: dict[str, object] | None = None


class BaseTool(ABC):
    """工具抽象基类。

    子类必须定义 name / description / skill / parameters 类属性，
    并实现 execute 方法。
    """

    name: ClassVar[str]
    description: ClassVar[str]
    #: 所属技能分组（用于按 skill 过滤/展示）
    skill: ClassVar[str] = "general"
    parameters: ClassVar[dict[str, object]]

    def schema(self) -> dict[str, object]:
        """生成 OpenAI 格式的工具声明（function calling schema）。

        Returns:
            dict[str, object]: tools 参数中单个工具的完整声明
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @abstractmethod
    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        """执行工具。

        Args:
            args: 工具入参（模型输出经 JSON 解析后的字典）
            user: 当前用户（用于权限校验）

        Returns:
            ToolResult: 执行结果
        """


class NavigateTool(BaseTool):
    """跳转工具：引导用户进入系统指定入口。

    权限规则：入口清单中 permission 为空的页面登录即可访问；
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
            return ToolResult(content="未知页面标识，请只从系统入口清单中选择页面")
        if not self._has_access(entry["permission"], user):
            logger.warning(f"AI 助手跳转被拒：user={user.id} page={page}")
            return ToolResult(
                content="当前用户无权访问该页面，请推荐其他入口",
                event_type=AssistantEventType.DENIED,
            )
        return ToolResult(
            content=f"NAVIGATE:{page}",
            event_type=AssistantEventType.NAVIGATE,
            event_data={"path": entry["path"]},
        )

    @staticmethod
    def _has_access(required_permission: str, user: CurrentUser) -> bool:
        """判断当前用户是否有权访问入口。

        Args:
            required_permission: 入口所需权限码（空 = 无需权限）
            user: 当前用户

        Returns:
            bool: 是否有权访问
        """
        if not required_permission:
            return True
        return "*" in user.permissions or required_permission in user.permissions


class ToolSource(ABC):
    """工具来源抽象接口。

    聚合不同来源的工具：内置代码工具 / 预留 MCP 服务器工具等。
    """

    @abstractmethod
    def load_tools(self) -> list[BaseTool]:
        """加载本来源的工具列表。

        Returns:
            list[BaseTool]: 工具实例列表（可为空）
        """


class BuiltinToolSource(ToolSource):
    """内置工具来源：注册系统内建工具。"""

    def load_tools(self) -> list[BaseTool]:
        return [NavigateTool()]


class MCPToolSource(ToolSource):
    """MCP（Model Context Protocol）工具来源（预留）。

    当前仅保留接入位：配置 ai.tools.mcp_enabled=true 时由依赖工厂注册，
    返回空工具集并记录告警日志；后续实现 MCP 客户端后在此加载远端工具。
    """

    def __init__(self, server_url: str = "") -> None:
        """初始化 MCP 工具来源。

        Args:
            server_url: MCP 服务器地址（预留）
        """
        self._server_url: str = server_url

    def load_tools(self) -> list[BaseTool]:
        logger.warning("MCP 工具源尚未实现，返回空工具集（server_url=%s）", self._server_url)
        return []


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
