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

from src.infras.llm import ToolCall, ToolCallAccumulator, ToolCallDelta
from src.services.admin.assistant_service import AssistantService, _InlineToolCallGate


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
        assert _extract('{"action": "navigate"}') is None


class TestToolCallAccumulator:
    """流式工具调用碎片累积器测试（纯内存拼装）。"""

    def test_single_call_fragments_assembled(self):
        """单个工具调用：id/name 首片段、arguments 多片段，应完整拼接。"""
        accumulator = ToolCallAccumulator()
        accumulator.add(ToolCallDelta(index=0, call_id="call_1", name="navigate"))
        accumulator.add(ToolCallDelta(index=0, arguments_delta='{"page":'))
        accumulator.add(ToolCallDelta(index=0, arguments_delta='"users"}'))
        calls = accumulator.build()
        assert len(calls) == 1
        assert calls[0] == ToolCall(id="call_1", name="navigate", arguments='{"page":"users"}')

    def test_parallel_calls_ordered_by_index(self):
        """同流并行两个工具调用：结果按 index 升序、参数互不串台。"""
        accumulator = ToolCallAccumulator()
        accumulator.add(ToolCallDelta(index=1, call_id="call_b", name="navigate", arguments_delta='{"page":"roles"}'))
        accumulator.add(ToolCallDelta(index=0, call_id="call_a", name="navigate", arguments_delta='{"page":"users"}'))
        calls = accumulator.build()
        assert [call.id for call in calls] == ["call_a", "call_b"]
        assert json.loads(calls[0].arguments) == {"page": "users"}
        assert json.loads(calls[1].arguments) == {"page": "roles"}

    def test_missing_fields_use_defaults(self):
        """仅到达 arguments 碎片时：id/name 用占位值，不抛异常。"""
        accumulator = ToolCallAccumulator()
        accumulator.add(ToolCallDelta(index=2, arguments_delta="{}"))
        calls = accumulator.build()
        assert calls[0].id == "call_2"
        assert calls[0].name == ""
        assert calls[0].arguments == "{}"

    def test_empty_accumulator_builds_nothing(self):
        """无任何碎片时返回空列表。"""
        assert ToolCallAccumulator().build() == []


class TestInlineToolCallGate:
    """流式正文内联工具调用检测门测试。"""

    def test_normal_text_passes_immediately(self):
        """普通首字符：立即放行，不扣留。"""
        gate = _InlineToolCallGate()
        assert gate.feed("怎么添加用户？") == ["怎么添加用户？"]
        assert not gate.is_holding

    def test_leading_whitespace_then_text_released_together(self):
        """前导空白期间等待，首字符正常时连同空白一起放行。"""
        gate = _InlineToolCallGate()
        assert gate.feed("   ") == []
        assert gate.feed("你好") == ["   你好"]

    def test_xml_tool_call_held_to_end(self):
        """完整 <tool_call> XML：持续扣留，流终仍处扣留态。"""
        gate = _InlineToolCallGate()
        payload = "<tool_call><tool_name>navigate</tool_name>"
        assert gate.feed(payload) == []
        assert gate.feed('<page>users</page></tool_call>') == []
        assert gate.is_holding

    def test_xml_broken_prefix_releases(self):
        """XML 前缀不匹配时立即补发扣留内容并转直放。"""
        gate = _InlineToolCallGate()
        assert gate.feed("<to") == []
        assert gate.feed("xxx") == ["<toxxx"]
        assert not gate.is_holding

    def test_complete_json_held(self):
        """完整 JSON 工具调用：解析成功，扣留到流终。"""
        gate = _InlineToolCallGate()
        assert gate.feed('{"action":"navigate","page":"users"}') == []
        assert gate.is_holding

    def test_incomplete_json_held_while_edge_error(self):
        """未写完的 JSON：报错在增长边缘，继续等待。"""
        gate = _InlineToolCallGate()
        assert gate.feed('{"action":') == []
        assert gate.is_holding

    def test_markdown_link_released_quickly(self):
        """以 [ 开头的普通 Markdown 链接：内部报错后快速放行（约 3 字符）。"""
        gate = _InlineToolCallGate()
        gate.feed("[")
        gate.feed("链")
        released = gate.feed("接")
        assert released == ["[链接"]
        assert not gate.is_holding

    def test_valid_non_tool_json_released_after_final_judgement(self):
        """合法 JSON 但非工具调用（如配置示例）：终判后 release 原样放行。"""
        gate = _InlineToolCallGate()
        assert gate.feed('{"a": 1}') == []
        assert gate.is_holding
        assert gate.release() == '{"a": 1}'

    def test_bypass_state_feeds_everything(self):
        """转直放后后续增量整段返回。"""
        gate = _InlineToolCallGate()
        gate.feed("普通文本")
        assert gate.feed("后续内容") == ["后续内容"]


class TestBoundaryChunker:
    """边界感知切块测试（方案①）。"""

    def test_empty_text_yields_nothing(self):
        """空文本：无任何片段。"""
        assert list(AssistantService._chunk_text("")) == []

    def test_short_text_single_piece(self):
        """短于窗口：整块返回。"""
        assert list(AssistantService._chunk_text("短文本")) == ["短文本"]

    def test_cuts_at_chinese_sentence_boundary(self):
        """超长文本：非末块在句号处对齐，不劈开句子。"""
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。结尾"
        pieces = list(AssistantService._chunk_text(text))
        assert "".join(pieces) == text
        assert all(len(piece) <= 24 for piece in pieces)
        assert all(piece[-1] == "。" for piece in pieces[:-1])

    def test_hard_cut_when_no_boundary(self):
        """窗口内无任何边界字符：退回硬切，仍保证有界与无损。"""
        text = "字" * 100
        pieces = list(AssistantService._chunk_text(text))
        assert "".join(pieces) == text
        assert [len(piece) for piece in pieces] == [24, 24, 24, 24, 4]
