"""AI 助手工具子包：注册机制 + 内置工具集。

成员划分：
    - base      工具抽象（BaseTool / ToolResult / ToolArgs，含后端鉴权助手）
    - navigate  跳转工具 NavigateTool（引导用户进入系统指定入口）
    - query     只读查询工具（系统统计 / 用户查询 / 我的权限 / 生效公告 / 应用状态）
    - registry  工具注册表 ToolRegistry（schema 导出 + 按名分发）
    - sources   工具来源（BuiltinToolSource 内置 / MCPToolSource 预留）

工具安全边界：
    - 只读查询工具不产生任何写操作，输出不含密码、密钥、手机号等敏感字段
    - 鉴权一律在工具 execute 内后端校验（不信任模型 / 前端声明）

扩展约定：
    新增一个工具 = 继承 BaseTool 实现 execute + 在对应 ToolSource 的
    load_tools 返回实例，注册表与编排层零改动。
"""

from src.assistant.tools.base import BaseTool, ToolArgs, ToolResult
from src.assistant.tools.navigate import NavigateTool
from src.assistant.tools.query import (
    QueryAnnouncementsTool,
    QueryAppStatusTool,
    QueryMyPermissionsTool,
    QuerySystemStatsTool,
    QueryUserInfoTool,
)
from src.assistant.tools.registry import ToolRegistry
from src.assistant.tools.sources import BuiltinToolSource, MCPToolSource, ToolSource

__all__ = [
    "BaseTool",
    "ToolArgs",
    "ToolResult",
    "NavigateTool",
    "QueryAnnouncementsTool",
    "QueryAppStatusTool",
    "QueryMyPermissionsTool",
    "QuerySystemStatsTool",
    "QueryUserInfoTool",
    "ToolRegistry",
    "ToolSource",
    "BuiltinToolSource",
    "MCPToolSource",
]
