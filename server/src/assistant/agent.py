#!/usr/bin/env python3
"""Agent 推理：流式 function calling 的单回合三分支决策。

TL;DR —— 本模块做什么：
    驱动「LLM 流式推理 → 三分支决策 → 工具执行 → 最终回答」的单回合流程，
    逐事件产出 SSE 数据。持久化、摘要、审计等写路径经构造时注入的回调
    端口委托给调用方（AssistantService），本模块自身零仓储依赖。

如何使用（装配在 AssistantService.__init__）：
    agent = AssistantAgent(
        llm_provider=service._llm_provider,
        tool_registry=registry,
        finish_round=service._finish_round,                    # 轮次收尾
        navigate_reply_builder=service._build_navigate_reply,  # 导航兜底回复
        navigate_auditor=service._audit_navigate,              # 跳转审计
    )
    messages = memory_facade.build_context(...)   # 上下文由调用方组装
    messages.append({"role": "user", "content": query})
    yield from agent.run(conversation, user, query, messages, operator)

ReAct 对应关系：
    reasoning 透出 = Thought；tool_calls = Action；tool 结果回填 = Observation

三分支决策（一次流式推理结束后，互斥且有序）：
    1. 结构化 tool_calls → 执行工具 → 流式生成最终回答；
    2. 文本形式工具调用（检测门已扣留，见 src/assistant/text_call.py）
       → 识别后执行，正文不泄漏；
    3. 普通回答 → 正文已实时呈现，交回调收尾。

工具回合（当前能力边界）：
    本模块为「单回合」：一次用户提问内最多发生 1 次工具调用，工具执行后
    以不带 tools 的流式调用强制收尾（模型只能给文字答案，不能再发起工具）。
    这覆盖了当前唯一工具 navigate 的场景，且天然不存在多工具死循环。
    后续若需要 A 工具结果→再调 B 工具的多步链路，再把 run 改造成带回环的
    ReAct 多轮循环（工具结果回填后回到推理起点，并补回步数上限保护）。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TypeAlias, cast

from src.assistant.text_call import InlineToolCallGate, extract_text_tool_call
from src.assistant.tools import ToolArgs, ToolRegistry
from src.constants.assistant import (
    ASSISTANT_CHUNK_BOUNDARY_CHARS,
    ASSISTANT_EMPTY_REPLY_MESSAGE,
    ASSISTANT_TOKEN_CHUNK_SIZE,
    AssistantEventType,
)
from src.core.config import settings
from src.core.logger import logger
from src.infras.llm import (
    ChatMessage,
    ContentDelta,
    LLMProvider,
    ReasoningDelta,
    ToolCall,
    ToolCallAccumulator,
    ToolCallDelta,
)
from src.models.entities.assistant_entity import AssistantConversationEntity
from src.schemas.admin.auth import CurrentUser

#: 轮次收尾回调：落库助手消息 + DONE 先行，摘要/命名后置为尽力而为（由服务层提供）
RoundFinisher: TypeAlias = Callable[
    [AssistantConversationEntity, str, str], Iterator[dict[str, object]]
]
#: navigate 兜底回复构造回调：FAQ 命中返回标准答案，否则入口目录引导语
NavigateReplyBuilder: TypeAlias = Callable[[str, dict[str, object]], str]
#: 跳转审计回调：写入审计日志（失败静默，不阻断主流程）
NavigateAuditor: TypeAlias = Callable[
    [CurrentUser, int, dict[str, object], dict[str, object] | None], None
]


@dataclass
class RoundState:
    """单轮流式推理的中间状态（在流式首轮中累积，供三分支决策读取）。

    封装目的：避免 run 单回合流程中散落多个局部变量（tool_accumulator /
    content_parts / inline_gate），让流式首轮和分支决策之间只通过
    state 对象传递，新增字段时不影响方法签名。

    Attributes:
        tool_accumulator: 结构化工具调用碎片累积器
        content_parts: 正文增量片段列表（流结束后拼接为完整正文）
        inline_gate: 文本形式工具调用检测门（决定正文立即放行还是扣留观察）
    """

    tool_accumulator: ToolCallAccumulator = field(default_factory=ToolCallAccumulator)
    content_parts: list[str] = field(default_factory=list) 
    inline_gate: InlineToolCallGate = field(default_factory=InlineToolCallGate)

    @property
    def structured_tool_calls(self) -> list[ToolCall]:
        """流结束后取出累积完成的结构化工具调用列表。"""
        return self.tool_accumulator.build()

    @property
    def content(self) -> str:
        """拼接去空白后的完整正文。"""
        return "".join(self.content_parts).strip()

    @property
    def text_tool_call(self) -> ToolCall | None:
        """从正文中识别的文本形式工具调用（非工具调用文本返回 None）。"""
        return extract_text_tool_call(self.content)


class AssistantAgent:
    """Agent 推理编排器：流式 function calling（ReAct 风格，单回合）。

    职责边界（与 AssistantService 的分工）：
        - 本类：LLM 流式推理、三分支决策、最多一次工具执行、SSE 事件产出；
        - 服务层：上下文组装（MemoryFacade）、消息落库、摘要、命名、审计
          ——经构造时注入的回调端口接入，本类零仓储依赖。

    回调端口（均由 AssistantService 提供）：
        - finish_round: 轮次收尾（落库 + DONE 先行；摘要/命名后置尽力而为）
        - navigate_reply_builder: navigate 兜底回复（FAQ 命中 / 入口目录引导语）
        - navigate_auditor: 跳转审计落库（失败静默，不阻断主流程）

    不变式：
        - run() 为生成器：惰性执行，首事件在迭代时才产生；
        - 工具执行结果一律回填 messages（role="tool"），供最终回答引用；
        - 本类不写库、不 commit：所有持久化动作都在回调端口另一侧完成。
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        finish_round: RoundFinisher,
        navigate_reply_builder: NavigateReplyBuilder,
        navigate_auditor: NavigateAuditor,
    ) -> None:
        """初始化 agent 循环编排器。

        Args:
            llm_provider: 大模型提供者（由服务层构造时创建并注入）
            tool_registry: 工具注册表（schemas 供首轮调用，dispatch 执行工具）
            finish_round: 轮次收尾回调（落库 + DONE 先行，重活后置）
            navigate_reply_builder: navigate 兜底回复构造回调
            navigate_auditor: 跳转审计回调
        """
        self._llm_provider: LLMProvider = llm_provider
        self._tool_registry: ToolRegistry = tool_registry
        self._finish_round: RoundFinisher = finish_round
        self._build_navigate_reply: NavigateReplyBuilder = navigate_reply_builder
        self._audit_navigate: NavigateAuditor = navigate_auditor

    def run(
        self,
        conversation: AssistantConversationEntity,
        user: CurrentUser,
        query: str,
        messages: list[dict[str, object]],
        operator: dict[str, object] | None = None,
    ) -> Iterator[dict[str, object]]:
        """执行单回合推理：一次流式推理 → 互斥三分支决策。

        工具回合能力边界见模块 docstring：最多 1 次工具调用，执行后强制收尾。

        Args:
            conversation: 会话实体
            user: 当前用户（工具执行鉴权用）
            query: 本轮用户输入
            messages: 已组装的上下文消息（含本轮 user 消息，由调用方拼装）
            operator: 操作人上下文（navigate 审计用）

        Yields:
            dict[str, object]: SSE 事件字典
        """
        # 先发 THINKING 事件：LLM 首字可能延迟数秒，提前通知前端展示思考态，避免用户面对空白
        yield {"type": AssistantEventType.THINKING.mark}

        # ── 唯一一轮流式推理：思维链/正文实时透传，工具碎片同步累积 ──
        state = RoundState()
        yield from self._stream_first_round(messages, state)
        # ── 分支 1：结构化工具调用 ──
        if state.structured_tool_calls:
            yield from self._handle_structured_calls(
                state, messages, conversation, user, operator, query
            )
            return
        # ── 分支 2：文本形式工具调用（检测门仍扣留 → 正文从未泄漏）──
        # 文本形式工具调用是为了接住那些把工具调用写进正文的模型，保证跳转功能不因模型不守规矩而失效
        if state.text_tool_call is not None and state.inline_gate.is_holding:
            yield from self._handle_inline_call(
                state, messages, conversation, user, operator, query
            )
            return
        # ── 分支 3：普通回答（正文已实时呈现）──
        yield from self._handle_plain_answer(state, messages, conversation, query)

    def _stream_first_round(
        self,
        messages: list[dict[str, object]],
        state: RoundState,
    ) -> Iterator[dict[str, object]]:
        """流式首轮调用 LLM：思维链/正文实时透出，工具碎片同步累积。

        产出事件：
            - REASONING：思维链增量
            - TOKEN：正文增量（经检测门决定立即放行还是扣留观察）

        Args:
            messages: 对话消息列表
            state: 本轮中间状态（tool 碎片、正文片段、检测门由本方法写入）

        Yields:
            dict[str, object]: REASONING / TOKEN 事件
        """
        llm_cfg = settings.ai.llm
        for stream_event in self._llm_provider.chat_stream(
            messages=cast(ChatMessage, messages),
            tools=self._tool_registry.schemas(),
            temperature=llm_cfg.temperature,
            max_tokens=llm_cfg.max_tokens,
        ):
            # 模型“思考过程”的文字。直接包成 REASONING 事件 yield 给前端展示思考态， 不写 state
            # 思考过程不落库、不参与决策，看完即焚
            if isinstance(stream_event, ReasoningDelta):
                yield {
                    "type": AssistantEventType.REASONING.mark,
                    "content": stream_event.text,
                }

            # 背景：模型决定调工具时，一个完整的工具调用是被 拆成碎片 流式到达的（id 一片、name 一片、arguments 的 JSON 字符串一片一片）。单看任何一片都不完整
            # 解决：将所有碎片累积起来，等完整一个工具调用后再处理
            elif isinstance(stream_event, ToolCallDelta):
                state.tool_accumulator.add(stream_event)
            elif isinstance(stream_event, ContentDelta):
                # 正文：1️⃣先存底稿，2️⃣再经检测门决定立即放行还是扣留观察
                state.content_parts.append(stream_event.text)
                for piece in state.inline_gate.feed(stream_event.text):
                    yield {"type": AssistantEventType.TOKEN.mark, "content": piece}
            else:
                # 联合类型已穷尽（chat_stream 只产三类事件），理论不可达；
                # 防御未来新增事件类型时被静默误当正文透出
                logger.warning(f"agent 首轮流式收到未识别事件类型，已忽略：{type(stream_event).__name__}")

    def _handle_structured_calls(
        self,
        state: RoundState,
        messages: list[dict[str, object]],
        conversation: AssistantConversationEntity,
        user: CurrentUser,
        operator: dict[str, object] | None,
        query: str,
    ) -> Iterator[dict[str, object]]:
        """分支 1：结构化工具调用 → 执行工具 → 流式生成最终回答 → 收尾。

        Args:
            state: 本轮中间状态（读取 structured_tool_calls）
            messages: 对话消息列表（执行后回填 tool 结果）
            conversation: 会话实体
            user: 当前用户
            operator: 操作人上下文（navigate 审计落库用）
            query: 本轮用户输入（收尾标题归纳用）

        Yields:
            dict[str, object]: STEP / NAVIGATE / DENIED / TOKEN / DONE 事件
        """
        messages.append(assistant_tool_calls_message(state.structured_tool_calls))
        for tool_call in state.structured_tool_calls:
            yield from self._execute_tool_call(
                tool_call, conversation, user, messages, operator
            )
        yield {
            "type": AssistantEventType.STEP.mark,
            "content": "工具执行完成，正在生成回答...",
        }
        content = yield from self._stream_final_answer(messages, self._llm_provider)
        if not content:
            content = ASSISTANT_EMPTY_REPLY_MESSAGE
            yield {"type": AssistantEventType.TOKEN.mark, "content": content}
        yield from self._finish_round(conversation, query, content)

    def _handle_inline_call(
        self,
        state: RoundState,
        messages: list[dict[str, object]],
        conversation: AssistantConversationEntity,
        user: CurrentUser,
        operator: dict[str, object] | None,
        query: str,
    ) -> Iterator[dict[str, object]]:
        """分支 2：文本形式工具调用（检测门已扣留，正文从未泄漏给前端）。

        部分推理模型偶发把工具调用写进正文而非结构化 tool_calls，检测门
        在流式阶段已将其扣留。此处识别后交由正常工具执行链路处理，
        执行结果以 navigate 事件透出，回复正文用预设导航文案替代。

        Args:
            state: 本轮中间状态（读取 text_tool_call）
            messages: 对话消息列表（执行后回填 tool 结果）
            conversation: 会话实体
            user: 当前用户
            operator: 操作人上下文（navigate 审计落库用）
            query: 本轮用户输入

        Yields:
            dict[str, object]: STEP / NAVIGATE / TOKEN / DONE 事件
        """
        text_call = state.text_tool_call
        yield {
            "type": AssistantEventType.STEP.mark,
            "content": f"正在调用工具：{text_call.name}",
        }
        text_args = safe_parse_args(text_call)
        text_result = self._tool_registry.dispatch(text_call.name, text_args, user)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": text_call.id,
                "content": text_result.content,
            }
        )
        if text_result.event_type is AssistantEventType.NAVIGATE:
            yield {
                "type": AssistantEventType.NAVIGATE.mark,
                **(text_result.event_data or {}),
            }
            self._audit_navigate(
                user, conversation.id, text_result.event_data or {}, operator
            )
        reply = self._build_navigate_reply(query, text_result.event_data or {})
        for piece in chunk_text(reply):
            yield {"type": AssistantEventType.TOKEN.mark, "content": piece}
        yield from self._finish_round(conversation, query, reply)

    def _handle_plain_answer(
        self,
        state: RoundState,
        messages: list[dict[str, object]],
        conversation: AssistantConversationEntity,
        query: str,
    ) -> Iterator[dict[str, object]]:
        """分支 3：普通回答（正文已实时呈现；被扣留的合法非工具 JSON 在此放行）。

        若首轮流式未返回任何内容，再流式重试一次（不传 tools），
        仍为空则用兜底文案。

        Args:
            state: 本轮中间状态（读取 content / inline_gate）
            messages: 对话消息列表
            conversation: 会话实体
            query: 本轮用户输入（收尾标题归纳用）

        Yields:
            dict[str, object]: TOKEN / STEP / DONE 事件
        """
        # 被检测门扣留的合法非工具 JSON 在此放行
        if state.inline_gate.is_holding:
            held_text = state.inline_gate.release()
            for piece in chunk_text(held_text):
                yield {"type": AssistantEventType.TOKEN.mark, "content": piece}
        content = state.content
        if not content:
            # 兜底：首轮流式未返回任何内容，再流式重试一次
            yield {
                "type": AssistantEventType.STEP.mark,
                "content": "模型未返回内容，正在尝试重新生成...",
            }
            content = yield from self._stream_final_answer(messages, self._llm_provider)
            if not content:
                content = ASSISTANT_EMPTY_REPLY_MESSAGE
                yield {"type": AssistantEventType.TOKEN.mark, "content": content}
        yield from self._finish_round(conversation, query, content)

    def _execute_tool_call(
        self,
        tool_call: ToolCall,
        conversation: AssistantConversationEntity,
        user: CurrentUser,
        messages: list[dict[str, object]],
        operator: dict[str, object] | None,
    ) -> Iterator[dict[str, object]]:
        """执行单个结构化工具调用：STEP 提示 + 分发 + tool 消息回填 + 事件透出。

        Args:
            tool_call: 工具调用
            conversation: 会话实体
            user: 当前用户
            messages: 对话消息列表（执行后回填 tool 结果，供最终回答使用）
            operator: 操作人上下文（navigate 审计落库用）

        Yields:
            dict[str, object]: STEP / NAVIGATE / DENIED 事件
        """
        yield {
            "type": AssistantEventType.STEP.mark,
            "content": f"正在调用工具：{tool_call.name}",
        }
        args = safe_parse_args(tool_call)
        tool_result = self._tool_registry.dispatch(tool_call.name, args, user)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result.content,
            }
        )
        if tool_result.event_type is not None:
            yield {
                "type": tool_result.event_type.mark,
                **(tool_result.event_data or {}),
            }
            if tool_result.event_type is AssistantEventType.NAVIGATE:
                self._audit_navigate(user, conversation.id, tool_result.event_data or {}, operator)

    def _stream_final_answer(
        self,
        messages: list[dict[str, object]],
        llm_provider: LLMProvider,
    ) -> Iterator[dict[str, object]]:
        """不传 tools 的最终回答流式调用：实时透出 REASONING / TOKEN。

        用于两处：结构化工具执行完后的收尾回答；首轮流式为空时的重试。

        Args:
            messages: 已回填工具结果（或重试场景原样）的消息列表
            llm_provider: 大模型提供者

        Yields:
            dict[str, object]: REASONING / TOKEN 事件

        Returns:
            str: 拼接去空白后的完整正文（外层经 `yield from` 直接取此返回值）
        """
        answer_parts: list[str] = []
        for stream_event in llm_provider.chat_stream(
            messages=cast(ChatMessage, messages),
            temperature=settings.ai.llm.temperature,
            max_tokens=settings.ai.llm.max_tokens,
        ):
            if isinstance(stream_event, ReasoningDelta):
                yield {
                    "type": AssistantEventType.REASONING.mark,
                    "content": stream_event.text,
                }
            elif isinstance(stream_event, ContentDelta):
                answer_parts.append(stream_event.text)
                yield {"type": AssistantEventType.TOKEN.mark, "content": stream_event.text}
            else:
                # 此调用不传 tools，正常不会有 ToolCallDelta；
                # 防御未来新增事件类型（如用量统计）被静默吞掉
                logger.warning(f"agent 收尾流式收到未识别事件类型，已忽略：{type(stream_event).__name__}")
        return "".join(answer_parts).strip()


def chunk_text(text: str) -> Iterator[str]:
    """将整段文本按语句 / 短语边界切块（边界感知切片）。

    流式优先改造后，对话正文已是上游实时增量、无需切块；本函数仅服务于
    「本地一次性持有整段文本」的少量场景：文本工具调用的收尾回复、检测
    门终判后放行的内容。切块以 ASSISTANT_TOKEN_CHUNK_SIZE 为目标上限，
    并在窗口内从后往前找最近的断点字符（ASSISTANT_CHUNK_BOUNDARY_CHARS）
    对齐断点，避免劈开词句；窗口内无任何边界时退回硬切，保证有界推进。

    Args:
        text: 完整文本

    Yields:
        str: 边界对齐的文本片段
    """
    max_size = ASSISTANT_TOKEN_CHUNK_SIZE
    total = len(text)
    start = 0
    while start < total:
        end = min(start + max_size, total)
        if end < total:
            window = text[start:end]
            for offset in range(len(window) - 1, -1, -1):
                if window[offset] in ASSISTANT_CHUNK_BOUNDARY_CHARS:
                    end = start + offset + 1
                    break
        yield text[start:end]
        start = end


def safe_parse_args(tool_call: ToolCall) -> ToolArgs:
    """安全解析工具入参 JSON（解析失败时降级为原始字符串）。

    Args:
        tool_call: 工具调用

    Returns:
        ToolArgs: 入参字典
    """
    try:
        parsed = json.loads(tool_call.arguments)
        return parsed if isinstance(parsed, dict) else {"raw": tool_call.arguments}
    except json.JSONDecodeError:
        return {"raw": tool_call.arguments}


def assistant_tool_calls_message(tool_calls: list[ToolCall]) -> dict[str, object]:
    """把拼装完成的工具调用转成回填用的 assistant 原始消息。

    流式接口不会直接给出非流式的完整 message，需按 OpenAI 协议手工合成
    （content=None + tool_calls），保证后续 tool 消息携带 tool_call_id 时合法。

    Args:
        tool_calls: 完整工具调用列表

    Returns:
        dict[str, object]: assistant 消息字典
    """
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {"name": tool_call.name, "arguments": tool_call.arguments},
            }
            for tool_call in tool_calls
        ],
    }
