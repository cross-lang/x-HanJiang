#!/usr/bin/env python3
"""AssistantAgent 单回合三分支决策的单元测试。

测试 src/assistant/agent.py（现有 test_agent.py 仅覆盖 chunk_text 纯函数）：
    - 分支 3 普通回答：思维链 / 正文实时透出；首轮流式为空时重试；仍为空用兜底文案
    - 分支 1 结构化工具调用：碎片累积 → 执行工具 → NAVIGATE 事件 + 审计 → 收尾回答
    - 分支 2 文本形式工具调用：检测门扣留 → 识别执行 → 导航兜底回复切块透出
    - 未识别流事件类型：防御性告警忽略，不影响主流程
    - 辅助函数：safe_parse_args / assistant_tool_calls_message / RoundState.content

LLM 一律用脚本化 fake（chat_stream 产出预置事件序列），不触网。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from src.assistant.agent import (
    AssistantAgent,
    RoundState,
    assistant_tool_calls_message,
    safe_parse_args,
)
from src.assistant.tools import BaseTool, ToolArgs, ToolRegistry, ToolResult
from src.assistant.tools.navigate import NavigateTool
from src.constants.assistant import (
    ASSISTANT_EMPTY_REPLY_MESSAGE,
    AssistantEventType,
)
from src.infras.llm import (
    ContentDelta,
    LLMProvider,
    ReasoningDelta,
    ToolCall,
    ToolCallDelta,
)
from src.schemas.admin.auth import CurrentUser

# ============================================================
# 测试替身
# ============================================================


@dataclass
class _FakeConversation:
    """会话实体最小替身。"""

    id: int = 1


class _ScriptedLLM(LLMProvider):
    """LLM 替身：chat_stream 按调用次数依次产出预置事件序列。

    首轮推理（带 tools）产出 first_events；收尾/重试轮产出 final_events。
    """

    def __init__(self, first_events: list, final_events: list | None = None) -> None:
        self._first = first_events
        self._final = final_events or []
        self.call_count: int = 0
        self.tool_schemas_seen: list[list | None] = []

    def chat_stream(self, messages, tools=None, temperature=None, max_tokens=None) -> Iterator:
        self.call_count += 1
        self.tool_schemas_seen.append(tools)
        events = self._first if self.call_count == 1 else self._final
        yield from events

    def chat(self, messages, tools=None, temperature=None, max_tokens=None):
        raise NotImplementedError

    def summarize(self, text: str) -> str:
        raise NotImplementedError


class _NoteTool(BaseTool):
    """测试用只读工具：固定返回普通文本结果（不携带前端事件）。"""

    name = "query_note"
    description = "记录便签"
    parameters: dict = {"type": "object", "properties": {}}

    def execute(self, args: ToolArgs, user: CurrentUser) -> ToolResult:
        return ToolResult(content="便签已记录")


def _make_user(permissions: list[str] | None = None) -> CurrentUser:
    """构造测试用户（默认超管通配，便于 navigate 工具放行）。"""
    return CurrentUser(
        id=1,
        username="tester",
        email="tester@example.com",
        name="测试用户",
        status="enabled",
        permissions=permissions if permissions is not None else ["*"],
    )


def _make_agent(llm: LLMProvider) -> tuple[AssistantAgent, list, list]:
    """组装 agent + 预置真实 navigate 工具与便签工具，返回 (agent, 收尾记录, 审计记录)。"""
    registry = ToolRegistry()
    registry.register(NavigateTool())
    registry.register(_NoteTool())

    finished: list[str] = []
    audited: list[dict] = []

    def _finish_round(conversation, query, content):
        finished.append(content)
        yield {"type": AssistantEventType.DONE.mark, "message_id": 999}

    def _nav_reply(query: str, event_data: dict) -> str:
        return f"已为你跳转至 {event_data.get('path') or '相关页面'}"

    def _audit(user, conversation_id, event_data, operator=None):
        audited.append({"conversation_id": conversation_id, "path": event_data.get("path")})

    agent = AssistantAgent(
        llm_provider=llm,
        tool_registry=registry,
        finish_round=_finish_round,
        navigate_reply_builder=_nav_reply,
        navigate_auditor=_audit,
    )
    return agent, finished, audited


def _run(agent: AssistantAgent, query: str = "打开用户管理") -> list[dict]:
    """执行一轮并收集全部事件。"""
    messages: list[dict] = [{"role": "user", "content": query}]
    return list(agent.run(_FakeConversation(id=1), _make_user(), query, messages, operator=None))


def _types(events: list[dict]) -> list[str]:
    """提取事件类型序列（便于断言）。"""
    return [e["type"] for e in events]


# ============================================================
# 分支 3：普通回答
# ============================================================


class TestPlainAnswerBranch:
    """普通回答分支测试。"""

    def test_reasoning_and_content_streamed(self):
        """思维链透传为 REASONING；正文增量透传为 TOKEN；收尾回调拿到完整正文。"""
        llm = _ScriptedLLM(
            first_events=[
                ReasoningDelta(text="让我想想"),
                ContentDelta(text="你好"),
                ContentDelta(text="，世界"),
            ]
        )
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        assert events[0]["type"] == AssistantEventType.THINKING.mark
        assert {"type": AssistantEventType.REASONING.mark, "content": "让我想想"} in events
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert token_text == "你好，世界"
        # 首轮带 tools 声明；收尾回调内容为拼接去空白后的完整正文
        assert llm.tool_schemas_seen[0]  # 首轮传出工具 schema
        assert finished == ["你好，世界"]

    def test_empty_first_round_retries(self):
        """首轮流式无正文：下发重试步骤事件，再无 tools 流式一次。"""
        llm = _ScriptedLLM(
            first_events=[],
            final_events=[ContentDelta(text="重试后的答案")],
        )
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        step_texts = [e["content"] for e in events if e["type"] == AssistantEventType.STEP.mark]
        assert any("重新生成" in t for t in step_texts)
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert token_text == "重试后的答案"
        assert finished == ["重试后的答案"]
        # 首轮传 tools，收尾轮不传（强制模型只给文字答案）
        assert llm.tool_schemas_seen[0]
        assert llm.tool_schemas_seen[1] is None

    def test_both_rounds_empty_use_fallback(self):
        """两轮流式均无内容：使用空回复兜底文案。"""
        llm = _ScriptedLLM(first_events=[], final_events=[])
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert token_text == ASSISTANT_EMPTY_REPLY_MESSAGE
        assert finished == [ASSISTANT_EMPTY_REPLY_MESSAGE]


# ============================================================
# 分支 1：结构化工具调用
# ============================================================


class TestStructuredToolBranch:
    """结构化 function calling 分支测试。"""

    def test_navigate_tool_called_and_audited(self):
        """navigate 碎片累积完成 → 执行 → NAVIGATE 事件 + 审计 → 流式收尾回答。"""
        llm = _ScriptedLLM(
            first_events=[
                ToolCallDelta(index=0, call_id="call_1", name="navigate", arguments_delta='{"page":'),
                ToolCallDelta(index=0, arguments_delta='"users"}'),
            ],
            final_events=[ContentDelta(text="已为你打开用户管理页面")],
        )
        agent, finished, audited = _make_agent(llm)
        events = _run(agent)
        types = _types(events)
        assert AssistantEventType.NAVIGATE.mark in types
        nav_event = next(e for e in events if e["type"] == AssistantEventType.NAVIGATE.mark)
        assert nav_event["path"] == "/users"
        # 审计被调用一次（navigate 动作）
        assert audited == [{"conversation_id": 1, "path": "/users"}]
        # 收尾回答透出并落库
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert "用户管理页面" in token_text
        assert finished == ["已为你打开用户管理页面"]

    def test_plain_tool_without_event(self):
        """普通工具（无前端事件）：执行后回填 tool 消息，直接流式收尾。"""
        llm = _ScriptedLLM(
            first_events=[
                ToolCallDelta(index=0, call_id="call_2", name="query_note", arguments_delta="{}"),
            ],
            final_events=[ContentDelta(text="便签处理完毕")],
        )
        agent, finished, audited = _make_agent(llm)
        events = _run(agent)
        types = _types(events)
        assert AssistantEventType.NAVIGATE.mark not in types
        assert audited == []  # 非 navigate 动作不写审计
        assert finished == ["便签处理完毕"]

    def test_final_answer_empty_after_tool_uses_fallback(self):
        """工具执行后收尾流式仍无内容：下发空回复兜底文案。"""
        llm = _ScriptedLLM(
            first_events=[
                ToolCallDelta(index=0, call_id="call_3", name="query_note", arguments_delta="{}"),
            ],
            final_events=[],
        )
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert token_text == ASSISTANT_EMPTY_REPLY_MESSAGE
        assert finished == [ASSISTANT_EMPTY_REPLY_MESSAGE]

    def test_final_answer_streams_reasoning(self):
        """收尾轮的思维链增量同样透传为 REASONING 事件。"""
        llm = _ScriptedLLM(
            first_events=[
                ToolCallDelta(index=0, call_id="call_4", name="query_note", arguments_delta="{}"),
            ],
            final_events=[ReasoningDelta(text="收尾思考"), ContentDelta(text="收尾正文")],
        )
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        assert {"type": AssistantEventType.REASONING.mark, "content": "收尾思考"} in events
        assert finished == ["收尾正文"]


# ============================================================
# 分支 2：文本形式工具调用
# ============================================================


class TestInlineToolBranch:
    """正文内联工具调用分支测试。"""

    def test_inline_navigate_xml(self):
        """模型把 navigate 写成 XML 正文：检测门扣留，执行后 NAVIGATE + 兜底回复切块透出。"""
        xml_text = "<tool_call><tool_name>navigate</tool_name><page>users</page></tool_call>"
        llm = _ScriptedLLM(first_events=[ContentDelta(text=xml_text)])
        agent, finished, audited = _make_agent(llm)
        events = _run(agent)
        types = _types(events)
        assert types[0] == AssistantEventType.THINKING.mark
        # 正文从未泄漏为普通 TOKEN（全部被扣留并替换为导航兜底回复）
        nav_event = next(e for e in events if e["type"] == AssistantEventType.NAVIGATE.mark)
        assert nav_event["path"] == "/users"
        assert audited == [{"conversation_id": 1, "path": "/users"}]
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert "已为你跳转" in token_text
        assert xml_text not in token_text  # 工具调用结构不回吐给用户
        assert finished == [token_text]

    def test_inline_function_json_without_event(self):
        """模型把 function 调用写成 JSON 正文：执行非 navigate 工具，不发 NAVIGATE。"""
        json_text = '{"tool_calls": [{"function": {"name": "query_note", "arguments": "{}"}}]}'
        llm = _ScriptedLLM(first_events=[ContentDelta(text=json_text)])
        agent, finished, audited = _make_agent(llm)
        events = _run(agent)
        assert AssistantEventType.NAVIGATE.mark not in _types(events)
        assert audited == []
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert "已为你跳转" in token_text  # navigate_reply_builder 兜底文案
        assert finished == [token_text]

    def test_held_non_tool_json_released_in_plain_branch(self):
        """被扣留但终判非工具调用的 JSON：在普通回答分支放行（切块透出）。"""
        # 合法但无工具语义的 JSON：检测门完整解析后扣留，终判非工具调用 → 放行
        held_text = '{"普通键": "普通值"}'
        llm = _ScriptedLLM(first_events=[ContentDelta(text=held_text)])
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert held_text in token_text
        assert finished == [held_text]

    def test_handle_inline_call_defense_when_text_call_none(self):
        """直接调用 _handle_inline_call 且状态中无文本工具调用：防御性直接返回。"""
        llm = _ScriptedLLM(first_events=[])
        agent, finished, _ = _make_agent(llm)
        state = RoundState()  # content 为空 → text_tool_call 为 None
        messages: list[dict] = []
        result = list(
            agent._handle_inline_call(state, messages, _FakeConversation(id=1), _make_user(), messages, "问题")
        )
        assert result == []
        assert finished == []


# ============================================================
# 防御分支：未识别事件类型
# ============================================================


class TestUnknownEventDefense:
    """流产出未识别事件类型时告警忽略，不中断主流程。"""

    def test_unknown_event_ignored_in_first_round(self):
        """首轮收到非三类增量对象：记 warning 并忽略，正文正常收尾。"""
        llm = _ScriptedLLM(
            first_events=["不明对象", ContentDelta(text="正常回答")],
        )
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert token_text == "正常回答"
        assert finished == ["正常回答"]

    def test_unknown_event_ignored_in_final_answer(self):
        """收尾轮收到未识别事件：同样忽略。"""
        llm = _ScriptedLLM(
            first_events=[],
            final_events=["不明对象", ContentDelta(text="重试答案")],
        )
        agent, finished, _ = _make_agent(llm)
        events = _run(agent)
        token_text = "".join(e["content"] for e in events if e["type"] == AssistantEventType.TOKEN.mark)
        assert token_text == "重试答案"


# ============================================================
# 辅助纯函数
# ============================================================


class TestHelpers:
    """agent 模块纯辅助函数测试。"""

    def test_safe_parse_valid_dict(self):
        """合法 JSON 对象：原样返回字典。"""
        args = safe_parse_args(ToolCall(id="1", name="navigate", arguments='{"page": "users"}'))
        assert args == {"page": "users"}

    def test_safe_parse_non_dict_falls_back(self):
        """JSON 非对象（如数组）：降级为 {"raw": 原文}。"""
        args = safe_parse_args(ToolCall(id="1", name="x", arguments="[1,2]"))
        assert args == {"raw": "[1,2]"}

    def test_safe_parse_invalid_json_falls_back(self):
        """JSON 解析失败：降级为 {"raw": 原文}。"""
        args = safe_parse_args(ToolCall(id="1", name="x", arguments="{坏"))
        assert args == {"raw": "{坏"}

    def test_assistant_tool_calls_message_shape(self):
        """拼装回填用的 assistant 原始消息：content=None + tool_calls 结构。"""
        msg = assistant_tool_calls_message([ToolCall(id="call_9", name="navigate", arguments='{"page":"/users"}')])
        assert msg["role"] == "assistant"
        assert msg["content"] is None
        assert msg["tool_calls"][0]["id"] == "call_9"
        assert msg["tool_calls"][0]["function"]["name"] == "navigate"

    def test_round_state_content_strips_whitespace(self):
        """RoundState.content 拼接并去除首尾空白。"""
        state = RoundState()
        state.content_parts = ["  你好", "世界  "]
        assert state.content == "你好世界"
