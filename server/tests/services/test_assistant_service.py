#!/usr/bin/env python3
"""
AI 助手文本工具调用识别测试

测试 AssistantService._extract_text_tool_call 在各类模型文本输出形式下的行为：
    - XML 标签形式
    - JSON 对象（navigate 动作：page / path / action_input）
    - JSON 数组（navigate 动作数组、function 调用数组）
    - OpenAI 文本形式（tool_calls 数组）
    - 普通文本 / 非法 JSON（应返回 None，避免误识别）
"""

import json

from src.infras.llm import ToolCall
from src.services.admin.assistant_service import AssistantService


def _extract(content: str | None) -> ToolCall | None:
    return AssistantService._extract_text_tool_call(content)


class TestExtractTextToolCall:
    """文本工具调用识别单元测试（纯函数，无数据库依赖）。"""

    def test_navigate_array_with_action_input_dict(self):
        """故障回归：模型输出 JSON 数组 + action_input 为嵌套 dict 时应识别跳转。"""
        call = _extract('[{"action":"navigate","action_input":{"path":"/users"}}]')
        assert call is not None
        assert call.name == "navigate"
        assert json.loads(call.arguments) == {"page": "users"}

    def test_navigate_array_with_action_input_page(self):
        """数组元素 action_input 内嵌 page 字段。"""
        call = _extract('[{"action":"navigate","action_input":{"page":"roles"}}]')
        assert call is not None
        assert call.name == "navigate"
        assert json.loads(call.arguments) == {"page": "roles"}

    def test_navigate_dict_with_path(self):
        """JSON 对象：action + path（原有形式保持兼容）。"""
        call = _extract('{"action":"navigate","path":"/roles"}')
        assert call is not None
        assert call.name == "navigate"
        assert json.loads(call.arguments) == {"page": "roles"}

    def test_navigate_dict_with_page(self):
        """JSON 对象：action + page（原有形式保持兼容）。"""
        call = _extract('{"action":"navigate","page":"users"}')
        assert call is not None
        assert json.loads(call.arguments) == {"page": "users"}

    def test_navigate_dict_with_action_input_str(self):
        """JSON 对象：action_input 为页面标识字符串（原有形式保持兼容）。"""
        call = _extract('{"action":"navigate","action_input":"users"}')
        assert call is not None
        assert json.loads(call.arguments) == {"page": "users"}

    def test_navigate_dict_with_unknown_path_maps_to_empty(self):
        """path 不在入口清单时映射为空串（原有语义保持兼容）。"""
        call = _extract('{"action":"navigate","path":"/unknown-page"}')
        assert call is not None
        assert json.loads(call.arguments) == {"page": ""}

    def test_array_multiple_elements_takes_first(self):
        """数组多元素：取第一个可识别的 navigate 动作。"""
        call = _extract(
            '[{"action":"navigate","action_input":{"path":"/users"}},'
            '{"action":"navigate","page":"roles"}]'
        )
        assert call is not None
        assert json.loads(call.arguments) == {"page": "users"}

    def test_array_of_openai_function_calls(self):
        """数组元素为 OpenAI function 序列化（function 键）时应识别。"""
        call = _extract(
            '[{"id":"call_1","type":"function","function":{"name":"navigate",'
            '"arguments":"{\\"page\\":\\"users\\"}"}}]'
        )
        assert call is not None
        assert call.name == "navigate"
        assert call.arguments == '{"page":"users"}'

    def test_openai_text_tool_calls(self):
        """OpenAI 文本形式：顶层 tool_calls 数组（原有形式保持兼容）。"""
        call = _extract(
            '{"tool_calls":[{"function":{"name":"navigate",'
            '"arguments":"{\\"page\\":\\"users\\"}"}}]}'
        )
        assert call is not None
        assert call.name == "navigate"
        assert call.arguments == '{"page":"users"}'

    def test_xml_form(self):
        """XML 标签形式（原有形式保持兼容）。"""
        call = _extract("<tool_call><tool_name>navigate</tool_name><path>/users</path></tool_call>")
        assert call is not None
        assert call.name == "navigate"
        assert json.loads(call.arguments) == {"path": "/users"}

    def test_plain_text_returns_none(self):
        """普通问题文本不应被误识别为工具调用。"""
        assert _extract("怎么添加用户？") is None

    def test_non_json_text_returns_none(self):
        """非 JSON 文本不应被误识别为工具调用。"""
        assert _extract("你好，请帮我介绍一下系统功能。") is None

    def test_empty_content_returns_none(self):
        """空内容不应被误识别为工具调用。"""
        assert _extract("") is None
        assert _extract("   ") is None
        assert _extract(None) is None

    def test_json_array_of_plain_strings_returns_none(self):
        """数组但元素非对象时返回 None。"""
        assert _extract('["users", "roles"]') is None

    def test_navigate_action_without_args_returns_none(self):
        """action 为 navigate 但无任何定位参数时返回 None（保持原行为）。"""
        assert _extract('{"action":"navigate"}') is None
