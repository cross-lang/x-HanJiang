#!/usr/bin/env python3
"""工具来源抽象与内置实现。

工具来源（ToolSource）负责「一批工具从哪来」：
    - BuiltinToolSource：内置工具（跳转 + 只读查询），按请求会话组装数据仓储
    - MCPToolSource：外部 MCP 服务器工具（预留，受配置 ai.tools.mcp_enabled 控制）

扩展约定：新增内置工具 = 实现 BaseTool 子类 + 在 BuiltinToolSource.load_tools
返回实例；接入外部工具集 = 实现 ToolSource 子类并在服务层注册。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from src.assistant.tools.base import BaseTool
from src.assistant.tools.navigate import NavigateTool
from src.assistant.tools.query import (
    QueryAnnouncementsTool,
    QueryAppStatusTool,
    QueryMyPermissionsTool,
    QuerySystemStatsTool,
    QueryUserInfoTool,
)
from src.core.logger import logger
from src.repositories.announcement_repository import AnnouncementRepository
from src.repositories.dashboard_repository import DashboardRepository
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.repositories.user_repository import UserRepository


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
    """内置工具来源：跳转工具 + 只读查询工具。

    查询类工具依赖的数据仓储按请求会话组装（与请求共享同一 SQLAlchemy
    session，随请求结束自动关闭）；跳转工具为纯静态数据，无需会话。
    """

    def __init__(self, session: Session) -> None:
        """初始化内置工具来源。

        Args:
            session: 请求级数据库会话（查询工具的仓储数据来源）
        """
        self._session = session

    def load_tools(self) -> list[BaseTool]:
        """组装全部内置工具实例。

        Returns:
            list[BaseTool]: 工具实例列表（跳转 + 5 个只读查询）
        """
        return [
            NavigateTool(),
            QuerySystemStatsTool(DashboardRepository(session=self._session)),
            QueryUserInfoTool(UserRepository(session=self._session)),
            QueryMyPermissionsTool(),
            QueryAnnouncementsTool(AnnouncementRepository(session=self._session)),
            QueryAppStatusTool(OpenApiAppRepository(session=self._session)),
        ]


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
