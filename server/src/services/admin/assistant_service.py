#!/usr/bin/env python3
"""AI 助手编排服务。

职责（服务层收口业务规则与事务，禁止直接操作数据库 / HTTP 对象）：
    - 会话生命周期：按用户创建 / 校验归属 / 分页查询
    - 上下文组装：系统提示词（第 0 层）+ 滚动摘要（第 2 层）+ 最近原文（第 3 层）
    - agent 循环：ReAct 风格 —— openai function calling 原生循环
      （reasoning 透出 = Thought，tool_calls = Action，tool 结果回填 = Observation）
    - 工具分发：经 ToolRegistry（注册机制）执行，navigate 动作透出 SSE 并写审计
    - 滚动摘要：窗口外旧消息渐进压缩进 Conversation.summary（第 2 层记忆）
    - 反馈：用户 👍👎 写入 assistant_feedbacks（后续提示词调优数据源）

同步形态：全部 def 同步实现，由 FastAPI 同步接口在线程池中执行；
重 IO（大模型调用）使用 openai 同步客户端。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import cast

from src.assistant.knowledge import KnowledgeBase
from src.assistant.memory import MemoryManager, NullUserMemory, UserMemoryProvider
from src.assistant.retriever import RetrieverProvider
from src.assistant.title import generate_title
from src.assistant.tools import ToolArgs, ToolRegistry
from src.constants.assistant import (
    ASSISTANT_CHUNK_BOUNDARY_CHARS,
    ASSISTANT_EMPTY_REPLY_MESSAGE,
    ASSISTANT_ENTITY_TYPE,
    ASSISTANT_ENTRY_CATALOG,
    ASSISTANT_FALLBACK_MESSAGE,
    ASSISTANT_MESSAGE_LIST_LIMIT,
    ASSISTANT_TOKEN_CHUNK_SIZE,
    AssistantEventType,
    AssistantMessageRole,
)
from src.core.config import settings
from src.core.exceptions import ExternalServiceException, NotFoundException
from src.core.logger import logger
from src.infras.llm import (
    ChatMessage,
    ContentDelta,
    LLMProvider,
    ReasoningDelta,
    ToolCall,
    ToolCallAccumulator,
    ToolCallDelta,
    get_llm_provider,
)
from src.models.entities.assistant_entity import (
    AssistantConversationEntity,
    AssistantMessageEntity,
)
from src.repositories.assistant_repository import (
    AssistantConversationRepository,
    AssistantFeedbackRepository,
    AssistantMessageRepository,
)
from src.schemas.admin.assistant import FeedbackRequest
from src.schemas.admin.auth import CurrentUser


def _page_of_path(path: str) -> str | None:
    """入口路由路径 → 页面码（供文本工具调用兜底映射）。

    NavigateTool 入参使用入口页面码（page），而模型文本形式的工具调用
    常写出路由路径（path），需要在此换算。

    Args:
        path: 入口路由路径（如 /roles）

    Returns:
        str | None: 对应的页面码；不在入口目录中返回 None
    """
    for item in ASSISTANT_ENTRY_CATALOG:
        if item["path"] == path:
            return item["page"]
    return None


class _InlineToolCallGate:
    """流式正文内联工具调用检测门（服务层内部组件）。

    背景：流式优先改造后，正文增量会实时发给前端；但推理模型偶发把工具
    调用写进正文（<tool_call> XML 或 JSON，详见 _extract_text_tool_call），
    一旦透出无法收回。

    策略（对普通对话零延迟）：
        - 只扣留「首个非空白字符为 < / { / [」的回复进行观察；
        - 前缀一旦不可能匹配工具调用语法，立即补发扣留内容并转直放；
        - 流结束仍未排除嫌疑的，由调用方用 _extract_text_tool_call 终判：
          是工具调用则执行（内容从未泄漏），否则调用 release() 放行。

    状态流转：watch（尚未见首字符）→ bypass（直放）/ hold（扣留观察）。
    """

    _XML_TAG: str = "<tool_call>"

    def __init__(self) -> None:
        """初始化：watch 状态、空缓冲。"""
        self._state: str = "watch"
        self._buffer: str = ""

    def feed(self, text: str) -> list[str]:
        """接收一段正文增量，返回当前可安全放行的文本。

        Args:
            text: 正文增量

        Returns:
            list[str]: 可立即下发的片段（直放时为整段，扣留时为空列表）
        """
        if self._state == "bypass":
            return [text]
        self._buffer += text
        if self._state == "watch":
            stripped = self._buffer.lstrip()
            if not stripped:
                return []
            first = stripped[0]
            if first not in ("<", "{", "["):
                self._state = "bypass"
                release, self._buffer = self._buffer, ""
                return [release]
            self._state = "hold"
        return self._classify()

    def _classify(self) -> list[str]:
        """hold 状态下判断缓冲前缀是否仍可能是工具调用。

        Returns:
            list[str]: 排除嫌疑时返回全部扣留内容（同时转直放）；否则空列表
        """
        stripped = self._buffer.strip()
        if stripped[0] == "<":
            # XML：去空白缓冲必须仍是 <tool_call> 的前缀，或已含完整开标签
            compatible = self._XML_TAG.startswith(stripped) or stripped.startswith(self._XML_TAG)
            if not compatible:
                return self._release_all()
            return []
        # JSON：能解析 → 完整 JSON，扣留到流终；
        # 报错位置在「增长边缘」→ 可能只是未写完，继续等；
        # 报错位置在缓冲内部 → 追加文本无法修复，排除嫌疑立即放行。
        try:
            json.loads(self._buffer)
        except json.JSONDecodeError as exc:
            edge = len(self._buffer.rstrip())
            if exc.pos < edge - 1:
                return self._release_all()
        return []

    def _release_all(self) -> list[str]:
        """转直放并返回全部扣留内容。

        Returns:
            list[str]: 含全部扣留文本的单元素列表
        """
        self._state = "bypass"
        release, self._buffer = self._buffer, ""
        return [release]

    @property
    def is_holding(self) -> bool:
        """流结束时是否仍处扣留态（待调用方终判）。"""
        return self._state == "hold"

    def release(self) -> str:
        """终判非工具调用后放行扣留内容（仅 is_holding 时调用）。

        Returns:
            str: 全部扣留文本
        """
        held, self._buffer = self._buffer, ""
        self._state = "bypass"
        return held


class AssistantService:
    """AI 助手编排服务（特殊编排职责，不继承 BaseService，参考 AuthService 写法）。"""

    def __init__(
        self,
        conversation_repository: AssistantConversationRepository,
        message_repository: AssistantMessageRepository,
        feedback_repository: AssistantFeedbackRepository,
        llm_provider: LLMProvider | None = None,
        tool_registry: ToolRegistry | None = None,
        knowledge_base: KnowledgeBase | None = None,
        user_memory: UserMemoryProvider | None = None,
        retriever: RetrieverProvider | None = None,
    ) -> None:
        """初始化 AI 助手服务。

        Args:
            conversation_repository: 会话仓库
            message_repository: 消息仓库
            feedback_repository: 反馈仓库
            llm_provider: 大模型提供者（默认由工厂懒加载单例）
            tool_registry: 工具注册表（默认创建并注册内置工具）
            knowledge_base: 系统提示词组装器（默认使用空长期记忆实现）
            user_memory: 用户长期记忆提供者（第 1 层预留，默认空实现）
            retriever: 知识检索提供者（RAG 预留，默认按配置创建）
        """
        self._conversation_repository: AssistantConversationRepository = conversation_repository
        self._message_repository: AssistantMessageRepository = message_repository
        self._feedback_repository: AssistantFeedbackRepository = feedback_repository
        # LLM 提供者懒加载：仅对话链路需要；未配置 API Key 时，
        # 会话列表 / 反馈等非对话接口不应受影响
        self._llm_provider: LLMProvider | None = llm_provider
        self._tool_registry: ToolRegistry = tool_registry or self._build_default_registry()
        self._user_memory: UserMemoryProvider = user_memory or NullUserMemory()
        self._knowledge_base: KnowledgeBase = knowledge_base or KnowledgeBase(self._user_memory)
        # 记忆子系统：四层记忆统一编排（L0 委托知识库；存储端口注入仓储；
        # LLM 复用本服务懒加载实例，保证注入的 fake provider 生效）
        self._memory: MemoryManager = MemoryManager(
            knowledge_base=self._knowledge_base,
            conversation_store=conversation_repository,
            message_store=message_repository,
            retriever=retriever,
            llm_provider_getter=self._get_llm,
        )

    def _get_llm(self) -> LLMProvider:
        """懒加载 LLM 提供者（首次对话调用时初始化）。

        Returns:
            LLMProvider: LLM 提供者实例

        Raises:
            ExternalServiceException: 未配置 API Key 或初始化失败时抛出
        """
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    @staticmethod
    def _build_default_registry() -> ToolRegistry:
        """构建默认工具注册表（内置工具 + 按配置启用 MCP 工具源）。

        Returns:
            ToolRegistry: 已注册内置工具的注册表
        """
        from src.assistant.tools import BuiltinToolSource, MCPToolSource

        registry = ToolRegistry()
        registry.register_source(BuiltinToolSource())
        if settings.ai.tools.mcp_enabled:
            registry.register_source(MCPToolSource(server_url=settings.ai.tools.mcp_server_url))
        return registry

    # ── 对外查询（api 层调用） ─────────────────────────────────

    def create_conversation(self, user_id: int) -> AssistantConversationEntity:
        """为指定用户创建一个新会话。

        Args:
            user_id: 用户ID

        Returns:
            AssistantConversationEntity: 新建会话实体
        """
        created = self._conversation_repository.create(
            self._conversation_repository.model_class(user_id=user_id)
        )
        self._conversation_repository.commit()
        return created

    def list_conversations(self, user_id: int, limit: int = 20) -> list[AssistantConversationEntity]:
        """查询当前用户的会话列表。

        Args:
            user_id: 用户ID
            limit: 返回条数上限

        Returns:
            list[AssistantConversationEntity]: 会话实体列表
        """
        return self._conversation_repository.list_by_user(user_id, limit)

    def list_messages(self, conversation_id: int, user_id: int) -> list[AssistantMessageEntity]:
        """查询会话消息（校验归属）。

        Args:
            conversation_id: 会话ID
            user_id: 用户ID

        Returns:
            list[AssistantMessageEntity]: 消息实体列表（时间正序）

        Raises:
            NotFoundException: 会话不存在或不属于当前用户
        """
        conversation = self._conversation_repository.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundException(message="会话不存在")
        return self._message_repository.list_by_conversation(conversation_id, ASSISTANT_MESSAGE_LIST_LIMIT)

    def update_pinned(
        self,
        user_id: int,
        conversation_id: int,
        pinned: bool,
    ) -> AssistantConversationEntity:
        """置顶 / 取消置顶会话（校验归属）。

        Args:
            user_id: 当前用户ID
            conversation_id: 会话ID
            pinned: True 置顶 / False 取消置顶

        Returns:
            AssistantConversationEntity: 更新后的会话实体

        Raises:
            NotFoundException: 会话不存在或不属于当前用户
        """
        conversation = self._conversation_repository.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundException(message="会话不存在")
        self._conversation_repository.update_pinned(conversation_id, pinned)
        self._conversation_repository.commit()
        return conversation

    def delete_conversation(self, user_id: int, conversation_id: int) -> None:
        """删除会话（软删除：校验归属后标记 deleted_at，消息与反馈物理保留留档）。

        Args:
            user_id: 当前用户ID
            conversation_id: 会话ID

        Raises:
            NotFoundException: 会话不存在或不属于当前用户
        """
        conversation = self._conversation_repository.get_by_id(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundException(message="会话不存在")
        self._conversation_repository.soft_delete(conversation_id)
        self._conversation_repository.commit()

    def save_feedback(self, user_id: int, feedback: FeedbackRequest) -> None:
        """保存用户对消息的反馈（校验归属）。

        Args:
            user_id: 用户ID
            feedback: 反馈请求模型

        Raises:
            NotFoundException: 会话不存在或不属于当前用户
        """
        conversation = self._conversation_repository.get_by_id(feedback.conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise NotFoundException(message="会话不存在")
        self._feedback_repository.add_feedback(
            conversation_id=feedback.conversation_id,
            message_id=feedback.message_id,
            user_id=user_id,
            positive=feedback.positive,
            comment=feedback.comment,
        )
        self._feedback_repository.commit()

    # ── 对话主入口（SSE 事件流） ───────────────────────────────

    def chat_stream(
        self,
        user: CurrentUser,
        conversation_id: int | None,
        message: str,
        operator: dict[str, object] | None = None,
    ) -> Iterator[dict[str, object]]:
        """执行一轮对话，逐事件产出 SSE 数据。

        事件类型（AssistantEventType）：
            navigate / denied: 工具动作透出
            token:            回复文本增量
            error:            功能未启用 / 会话不存在 / 大模型服务异常（含兜底回复）
            done:             本轮结束（成功含 message_id；失败时 message_id 为空）

        异常处理约定（遵循分层规范）：
            本方法为 SSE 通道的服务端边界，业务异常（NotFoundException /
            ExternalServiceException）在此**服务层内**转为 error + done 事件，
            不向 api 层抛出；api 层兜底仅处理不可预期异常。

        Args:
            user: 当前用户
            conversation_id: 会话ID（为空则创建新会话）
            message: 用户输入
            operator: 操作人上下文（operator_id / operator_name / ip_address，
                由 api 层 get_user_operator_context 构造，navigate 审计落库用）

        Yields:
            dict[str, object]: SSE 事件字典
        """
        if not settings.ai.enabled:
            yield {"type": AssistantEventType.ERROR.mark, "message": "AI 助手功能未启用，请在配置中开启"}
            yield {"type": AssistantEventType.DONE.mark, "conversation_id": conversation_id, "message_id": None}
            return
        conversation: AssistantConversationEntity | None = None
        try:
            conversation = self._get_or_create_conversation(user.id, conversation_id)
            self._save_message(conversation.id, AssistantMessageRole.USER.value, message)
            yield from self._run_agent(conversation, user, message, operator)
        except NotFoundException as exc:
            # 会话不存在或归属不符：不落库，直接提示并结束
            yield {"type": AssistantEventType.ERROR.mark, "message": str(exc)}
            yield {"type": AssistantEventType.DONE.mark, "conversation_id": conversation_id, "message_id": None}
        except ExternalServiceException as exc:
            conv_id_log = conversation.id if conversation is not None else None
            logger.warning(f"AI 助手对话失败：conversation={conv_id_log} err={exc}")
            if conversation is not None:
                saved = self._save_message(
                    conversation.id,
                    AssistantMessageRole.ASSISTANT.value,
                    ASSISTANT_FALLBACK_MESSAGE,
                )
                message_id: int | None = saved.id
            else:
                message_id = None
            yield {"type": AssistantEventType.ERROR.mark, "message": str(exc)}
            yield {"type": AssistantEventType.DONE.mark, "conversation_id": conversation_id, "message_id": message_id}

    # ── 内部实现 ───────────────────────────────────────────────

    def _run_agent(
        self,
        conversation: AssistantConversationEntity,
        user: CurrentUser,
        query: str,
        operator: dict[str, object] | None = None,
    ) -> Iterator[dict[str, object]]:
        """agent 循环：流式优先的 function calling 循环（ReAct 风格）。

        与旧版的差异：首轮直接流式调用 —— 思维链与正文在模型生成的同时
        实时透出（消除「长时间只显示正在思考」的空等），工具调用碎片经
        ToolCallAccumulator 累积，流结束后按三分支决策：
            1. 结构化 tool_calls → 执行工具 → 流式生成最终回答；
            2. 无结构化调用但正文是「文本形式工具调用」→ 检测门已将其
               扣留（_InlineToolCallGate），识别后执行，内部结构不泄漏；
            3. 普通回答 → 正文已实时呈现，直接落库收尾。

        Args:
            conversation: 会话实体
            user: 当前用户
            query: 本轮输入
            operator: 操作人上下文（navigate 审计落库用）

        Yields:
            dict[str, object]: SSE 事件字典
        """
        messages: list[dict[str, object]] = self._memory.build_context(conversation, user.id, query)
        messages.append({"role": "user", "content": query})
        # 首字延迟兜底：进入 LLM 调用前先透出 thinking 事件，让前端立即展示思考态
        yield {"type": AssistantEventType.THINKING.mark}
        llm_cfg = settings.ai.llm
        llm_provider = self._get_llm()
        for _ in range(llm_cfg.max_tool_rounds):
            # ── 流式首轮：思维链/正文实时透传，工具碎片同步累积，正文过检测门 ──
            tool_accumulator = ToolCallAccumulator()
            content_parts: list[str] = []
            inline_gate = _InlineToolCallGate()
            for stream_event in llm_provider.chat_stream(
                messages=cast(ChatMessage, messages),
                tools=self._tool_registry.schemas(),
                temperature=llm_cfg.temperature,
                max_tokens=llm_cfg.max_tokens,
            ):
                if isinstance(stream_event, ReasoningDelta):
                    yield {
                        "type": AssistantEventType.REASONING.mark,
                        "content": stream_event.text,
                    }
                elif isinstance(stream_event, ToolCallDelta):
                    tool_accumulator.add(stream_event)
                else:
                    # ContentDelta：检测门决定立即放行还是扣留观察
                    content_parts.append(stream_event.text)
                    for piece in inline_gate.feed(stream_event.text):
                        yield {"type": AssistantEventType.TOKEN.mark, "content": piece}

            # ── 分支 1：结构化工具调用 ──
            structured_calls = tool_accumulator.build()
            if structured_calls:
                messages.append(self._assistant_tool_calls_message(structured_calls))
                for tool_call in structured_calls:
                    yield from self._execute_tool_call(
                        tool_call, conversation, user, messages, operator
                    )
                yield {
                    "type": AssistantEventType.STEP.mark,
                    "content": "工具执行完成，正在生成回答...",
                }
                content = yield from self._stream_final_answer(messages, llm_provider)
                if not content:
                    content = ASSISTANT_EMPTY_REPLY_MESSAGE
                    yield {"type": AssistantEventType.TOKEN.mark, "content": content}
                yield from self._finish_round(conversation, query, content)
                return

            # ── 分支 2：文本形式工具调用（检测门仍扣留 → 正文从未泄漏）──
            content = "".join(content_parts).strip()
            text_call = self._extract_text_tool_call(content)
            if text_call is not None and inline_gate.is_holding:
                yield {
                    "type": AssistantEventType.STEP.mark,
                    "content": f"正在调用工具：{text_call.name}",
                }
                text_args = self._safe_parse_args(text_call)
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
                for piece in self._chunk_text(reply):
                    yield {"type": AssistantEventType.TOKEN.mark, "content": piece}
                yield from self._finish_round(conversation, query, reply)
                return

            # ── 分支 3：普通回答（正文已实时呈现；被扣留的合法非工具 JSON 在此放行）──
            if inline_gate.is_holding:
                held_text = inline_gate.release()
                for piece in self._chunk_text(held_text):
                    yield {"type": AssistantEventType.TOKEN.mark, "content": piece}
            if not content:
                # 兜底：首轮流式未返回任何内容，再流式重试一次
                yield {
                    "type": AssistantEventType.STEP.mark,
                    "content": "模型未返回内容，正在尝试重新生成...",
                }
                content = yield from self._stream_final_answer(messages, llm_provider)
                if not content:
                    content = ASSISTANT_EMPTY_REPLY_MESSAGE
                    yield {"type": AssistantEventType.TOKEN.mark, "content": content}
            yield from self._finish_round(conversation, query, content)
            return

        # 达到工具步数上限仍无最终答案（异常兜底，避免死循环）
        saved = self._save_message(
            conversation.id, AssistantMessageRole.ASSISTANT.value, ASSISTANT_FALLBACK_MESSAGE
        )
        yield {"type": AssistantEventType.ERROR.mark, "message": "对话步骤超限，请重试"}
        yield self._done_event(conversation.id, saved.id)

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
        args = self._safe_parse_args(tool_call)
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
        return "".join(answer_parts).strip()

    @staticmethod
    def _assistant_tool_calls_message(tool_calls: list[ToolCall]) -> dict[str, object]:
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

    def _finish_round(
        self,
        conversation: AssistantConversationEntity,
        query: str,
        content: str,
    ) -> Iterator[dict[str, object]]:
        """一轮收尾：落库助手消息 + 滚动摘要 + 标题归纳 + DONE。

        Args:
            conversation: 会话实体
            query: 本轮用户输入（标题归纳用）
            content: 最终回复正文

        Yields:
            dict[str, object]: DONE 事件
        """
        saved = self._save_message(
            conversation.id, AssistantMessageRole.ASSISTANT.value, content
        )
        self._memory.roll_summary(conversation)
        self._maybe_rename(conversation, query, content)
        yield self._done_event(conversation.id, saved.id)

    @staticmethod
    def _chunk_text(text: str) -> Iterator[str]:
        """将整段文本按语句 / 短语边界切块（边界感知切片，方案①）。

        流式优先改造后，对话正文已是上游实时增量、无需切块；本方法仅服务于
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

    @staticmethod
    def _safe_parse_args(tool_call: ToolCall) -> ToolArgs:
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

    @staticmethod
    def _extract_text_tool_call(content: str | None) -> ToolCall | None:
        """从回复正文中识别模型以文本形式输出的工具调用（兜底）。

        部分推理模型（如 mimo-v2.5-pro）偶发把函数调用写进正文而非结构化
        tool_calls，常见形式：
            - XML：<tool_call><tool_name>navigate</tool_name><path>/roles</path></tool_call>
            - JSON 对象：{"action": "navigate", "path": "/roles"}
            或 OpenAI 文本形式：{"tool_calls": [{"function": {"name": ..., "arguments": ...}}]}
            - JSON 数组：[{"action": "navigate", "action_input": {"path": "/users"}}]
                （部分模型以数组形式输出候选动作，元素可为 navigate 动作或 function 调用）
        识别后转为 ToolCall，交由 agent 循环正常执行，避免把内部结构
        作为回复正文展示给用户。

        Args:
            content: 模型回复正文（可空）

        Returns:
            ToolCall | None: 识别出的工具调用；非工具调用文本返回 None
        """
        if not content or not content.strip():
            return None
        text = content.strip()
        # 形式 A：XML 标签
        xml_match = re.search(
            r"<tool_call>\s*<tool_name>(\w+)</tool_name>(.*?)</tool_call>",
            text,
            re.DOTALL,
        )
        if xml_match is not None:
            name: str = xml_match.group(1)
            args_xml: str = xml_match.group(2)
            args: dict[str, str] = {}
            for tag, value in re.findall(r"<(\w+)>([^<]+)</\1>", args_xml):
                args[tag] = value.strip()
            return ToolCall(id="text-call", name=name, arguments=json.dumps(args, ensure_ascii=False))
        # 形式 B：JSON 对象或数组（navigate 动作 / tool_calls / function 调用）
        try:
            payload: object = json.loads(text)
        except json.JSONDecodeError:
            return None
        candidates: list[object] = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            call = AssistantService._parse_text_call_item(item)
            if call is not None:
                return call
        return None

    @staticmethod
    def _parse_text_call_item(item: dict[str, object]) -> ToolCall | None:
        """从单个 JSON 对象识别文本工具调用。

        支持三类：
            1. navigate 动作：{"action": "navigate", "page"/"path"/"action_input"}
            2. tool_calls 数组：{"tool_calls": [{"function": {"name", "arguments"}}]}
            3. function 调用：{"function": {"name": ..., "arguments": ...}}（数组元素常见序列化）
        """
        action = item.get("action")
        if isinstance(action, str) and action == "navigate":
            return AssistantService._build_navigate_call(item)
        calls = item.get("tool_calls")
        if isinstance(calls, list) and calls:
            first: object = calls[0]
            if isinstance(first, dict):
                fn = first.get("function")
                if isinstance(fn, dict):
                    fn_name: object = fn.get("name")
                    fn_args: object = fn.get("arguments")
                    if isinstance(fn_name, str) and isinstance(fn_args, str):
                        return ToolCall(
                            id=str(first.get("id") or "text-call"),
                            name=fn_name,
                            arguments=fn_args,
                        )
        fn = item.get("function")
        if isinstance(fn, dict):
            fn_name = fn.get("name")
            fn_args = fn.get("arguments")
            if isinstance(fn_name, str) and isinstance(fn_args, str):
                return ToolCall(
                    id=str(item.get("id") or "text-call"),
                    name=fn_name,
                    arguments=fn_args,
                )
        return None

    @staticmethod
    def _build_navigate_call(item: dict[str, object]) -> ToolCall | None:
        """从 navigate 动作对象构造 ToolCall。

        支持 page / path / action_input 三种字段定位目标页；
        action_input 既可为字符串（页面标识或路由）也可为嵌套 dict（含 page/path）。

        Returns:
            ToolCall | None: 参数有效时返回 navigate 调用；参数缺失返回 None
        """
        page = item.get("page")
        if isinstance(page, str) and page:
            return ToolCall(
                id="text-call",
                name="navigate",
                arguments=json.dumps({"page": page}, ensure_ascii=False),
            )
        path = item.get("path")
        if isinstance(path, str) and path:
            mapped = _page_of_path(path)
            return ToolCall(
                id="text-call",
                name="navigate",
                arguments=json.dumps({"page": mapped if mapped is not None else ""}, ensure_ascii=False),
            )
        action_input = item.get("action_input")
        if isinstance(action_input, dict):
            sub_page = action_input.get("page")
            if isinstance(sub_page, str) and sub_page:
                return ToolCall(
                    id="text-call",
                    name="navigate",
                    arguments=json.dumps({"page": sub_page}, ensure_ascii=False),
                )
            sub_path = action_input.get("path")
            if isinstance(sub_path, str) and sub_path:
                mapped = _page_of_path(sub_path)
                return ToolCall(
                    id="text-call",
                    name="navigate",
                    arguments=json.dumps({"page": mapped if mapped is not None else ""}, ensure_ascii=False),
                )
        if isinstance(action_input, str) and action_input:
            mapped = _page_of_path(action_input)
            return ToolCall(
                id="text-call",
                name="navigate",
                arguments=json.dumps(
                    {"page": mapped if mapped is not None else action_input},
                    ensure_ascii=False,
                ),
            )
        return None

    def _build_navigate_reply(self, query: str, event_data: dict[str, object]) -> str:
        """为文本工具调用兜底生成自然语言收尾回复。

        优先返回 FAQ 命中条目的标准答案（给用户真实操作步骤）；
        未命中时基于入口目录描述给出跳转引导语。

        Args:
            query: 用户本轮提问
            event_data: 工具事件数据（含 path）

        Returns:
            str: 自然语言回复（不包含任何工具调用 JSON / XML 文本）
        """
        hit = self._knowledge_base.match_faq(query)
        if hit is not None:
            return hit.answer
        path = str(event_data.get("path") or "")
        if not path:
            return "抱歉，暂时无法为你跳转该页面；如需操作步骤可以继续问我。"
        entry = next((item for item in ASSISTANT_ENTRY_CATALOG if item["path"] == path), None)
        desc = str(entry["description"]) if entry is not None else "相关页面"
        return f"已为你打开「{desc}」页面，你可以在这里完成相关操作；需要更具体的步骤可以继续问我。"

    def _get_or_create_conversation(
        self,
        user_id: int,
        conversation_id: int | None,
    ) -> AssistantConversationEntity:
        """获取已有会话（校验归属）或创建新会话。

        Args:
            user_id: 用户ID
            conversation_id: 会话ID（可空）

        Returns:
            AssistantConversationEntity: 会话实体

        Raises:
            NotFoundException: 会话不存在或不属于当前用户
        """
        if conversation_id is not None:
            conversation = self._conversation_repository.get_by_id(conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise NotFoundException(message="会话不存在")
            return conversation
        created = self._conversation_repository.create(
            self._conversation_repository.model_class(user_id=user_id)
        )
        self._conversation_repository.commit()
        return created

    def _save_message(self, conversation_id: int, role: str, content: str) -> AssistantMessageEntity:
        """持久化一条会话消息。

        Args:
            conversation_id: 会话ID
            role: 消息角色（user / assistant）
            content: 消息内容

        Returns:
            AssistantMessageEntity: 新建消息实体
        """
        entity = self._message_repository.add_message(conversation_id, role, content)
        self._message_repository.commit()
        return entity

    def _maybe_rename(
        self,
        conversation: AssistantConversationEntity,
        query: str,
        reply: str,
    ) -> None:
        """为未命名会话归纳主题名（失败静默，不影响主流程）。

        仅当会话尚未命名时调用一次 LLM 生成标题；已有标题的会话
        不再每轮重复生成，避免每轮对话额外等待一次完整模型调用。

        Args:
            conversation: 会话实体
            query: 本轮用户输入
            reply: 本轮助手最终回复（兜底跳转文案或正常回答）
        """
        if conversation.title:
            return
        try:
            title = generate_title(
                self._get_llm(),
                summary=conversation.summary or "",
                query=query,
                reply=reply,
            )
            if not title:
                return
            self._conversation_repository.update_title(conversation.id, title)
            conversation.title = title
            self._conversation_repository.commit()
            logger.info(f"AI 助手会话命名：conversation={conversation.id} title={title}")
        except ExternalServiceException:
            logger.warning(f"AI 助手会话命名失败（模型调用异常）：conversation={conversation.id}")

    def _audit_navigate(
        self,
        user: CurrentUser,
        conversation_id: int,
        event_data: dict[str, object],
        operator: dict[str, object] | None = None,
    ) -> None:
        """记录 AI 助手跳转审计日志。

        Args:
            user: 当前用户
            conversation_id: 会话ID
            event_data: navigate 事件数据（含 path）
            operator: 操作人上下文（含 ip_address，由 api 层工厂构造后透传）
        """
        try:
            from src.services.admin.audit_service import AuditService

            AuditService().log_event(
                entity_type=ASSISTANT_ENTITY_TYPE,
                entity_id=conversation_id,
                action="navigate",
                operator_id=user.id,
                ip_address=(operator or {}).get("ip_address"),
                remarks=f"AI 助手跳转到 {event_data.get('path', '')}",
            )
        except Exception as exc:  # noqa: BLE001 - 审计失败不应阻断主流程
            logger.warning(f"AI 助手跳转审计写入失败: {exc}")

    @staticmethod
    def _done_event(conversation_id: int, message_id: int) -> dict[str, object]:
        """构造本轮结束事件（供前端续聊与反馈）。

        Args:
            conversation_id: 会话ID
            message_id: 最后一条助手消息ID

        Returns:
            dict[str, object]: done 事件
        """
        return {
            "type": AssistantEventType.DONE.mark,
            "conversation_id": conversation_id,
            "message_id": message_id,
        }
