#!/usr/bin/env python3
"""
LLM 基础设施单元测试

测试 src/infras/llm 中流式协议对象的行为：
    - ToolCallAccumulator：工具调用碎片的累积与拼装
"""

import json

from src.infras.llm import ToolCall, ToolCallAccumulator, ToolCallDelta


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
