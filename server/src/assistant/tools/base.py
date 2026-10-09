#!/usr/bin/env python3
"""工具抽象基类与结果契约。

本模块定义工具机制的最小公共集：
    - ToolArgs：工具入参类型别名（模型输出经 JSON 解析后的字典）
    - ToolResult：工具执行结果（回填给模型 + 可选透出前端的动作）
    - BaseTool：工具抽象基类（schema 导出 + execute 抽象 + 后端鉴权助手）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from src.constants.assistant import AssistantEventType
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

    @staticmethod
    def _has_access(required_permission: str, user: CurrentUser) -> bool:
        """判断当前用户是否拥有指定权限（后端鉴权，不信任模型 / 前端声明）。

        Args:
            required_permission: 所需权限码（空串 = 登录即可，无需权限）
            user: 当前用户

        Returns:
            bool: 是否有权（含 "*" 表示超级管理员通配）
        """
        if not required_permission:
            return True
        return "*" in user.permissions or required_permission in user.permissions
