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
from src.assistant.memory import NullUserMemory, UserMemoryProvider
from src.assistant.retriever import RetrieverProvider, get_retriever_provider
from src.assistant.title import generate_title
from src.assistant.tools import ToolArgs, ToolRegistry
from src.constants.assistant import (
    ASSISTANT_EMPTY_REPLY_MESSAGE,
    ASSISTANT_ENTITY_TYPE,
    ASSISTANT_ENTRY_CATALOG,
    ASSISTANT_FALLBACK_MESSAGE,
    ASSISTANT_MESSAGE_LIST_LIMIT,
    ASSISTANT_ROLL_CHUNK_SIZE,
    ASSISTANT_ROLL_TRIGGER_FACTOR,
    ASSISTANT_TOKEN_CHUNK_SIZE,
    AssistantEventType,
    AssistantMessageRole,
)
from src.core.config import settings
from src.core.exceptions import ExternalServiceException, NotFoundException
from src.core.logger import logger
from src.infras.llm import ChatMessage, LLMChatResult, LLMProvider, ToolCall, get_llm_provider
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
from src.utils.text import estimate_tokens


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
        self._retriever: RetrieverProvider = retriever or get_retriever_provider()

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
        """agent 循环：function calling 原生循环（ReAct 风格）。

        每轮：模型输出 → 若含工具调用则执行并回填 tool 消息后继续；
        无工具调用则流式输出最终答案并结束。

        Args:
            conversation: 会话实体
            user: 当前用户
            query: 本轮用户输入
            operator: 操作人上下文（navigate 审计落库用）

        Yields:
            dict[str, object]: SSE 事件字典
        """
        messages: list[dict[str, object]] = self._build_context(conversation, user.id, query)
        messages.append({"role": "user", "content": query})
        # 首字延迟兜底：进入 LLM 调用前先透出 thinking 事件，
        # 让前端立即展示"思考中"状态，避免非流式 chat() 期间的空白等待
        yield {"type": AssistantEventType.THINKING.mark}
        llm_cfg = settings.ai.llm
        llm_provider = self._get_llm()
        for _ in range(llm_cfg.max_tool_rounds):
            result: LLMChatResult = llm_provider.chat(
                messages=cast(ChatMessage, messages),
                tools=self._tool_registry.schemas(),
                temperature=llm_cfg.temperature,
                max_tokens=llm_cfg.max_tokens,
            )
            messages.append(result.raw_message)  # 原样回填助手消息（含工具调用）
            if result.tool_calls:
                for tool_call in result.tool_calls:
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
                            self._audit_navigate(
                                user, conversation.id, tool_result.event_data or {}, operator
                            )
                # 工具执行完直接流式输出最终回复（不再非式再问一轮，避免 navigate 后长时间等待）
                answer_chunks: list[str] = []
                for chunk in llm_provider.chat_stream(
                    messages=cast(ChatMessage, messages),
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                ):
                    answer_chunks.append(chunk)
                    yield {"type": AssistantEventType.TOKEN.mark, "content": chunk}
                content = "".join(answer_chunks).strip()
                if not content:
                    content = ASSISTANT_EMPTY_REPLY_MESSAGE
                    yield {"type": AssistantEventType.TOKEN.mark, "content": content}
                saved = self._save_message(conversation.id, AssistantMessageRole.ASSISTANT.value, content)
                self._maybe_roll_summary(conversation)
                self._maybe_rename(conversation, query, content)
                yield self._done_event(conversation.id, saved.id)
                return
            # 兜底：推理模型偶发把工具调用写成正文文本（JSON / XML），
            # 识别并转成真实动作，避免把内部 JSON 原样透传给用户
            text_call = self._extract_text_tool_call(result.content)
            if text_call is not None:
                text_args = self._safe_parse_args(text_call)
                text_result = self._tool_registry.dispatch(text_call.name, text_args, user)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": text_call.id,
                        "content": text_result.content,
                    }
                )
                if text_result.event_type is not None:
                    yield {
                        "type": text_result.event_type.mark,
                        **(text_result.event_data or {}),
                    }
                    if text_result.event_type is AssistantEventType.NAVIGATE:
                        self._audit_navigate(
                            user, conversation.id, text_result.event_data or {}, operator
                        )
                reply = self._build_navigate_reply(query, text_result.event_data or {})
                yield {"type": AssistantEventType.TOKEN.mark, "content": reply}
                saved = self._save_message(conversation.id, AssistantMessageRole.ASSISTANT.value, reply)
                self._maybe_roll_summary(conversation)
                self._maybe_rename(conversation, query, reply)
                yield self._done_event(conversation.id, saved.id)
                return
            # 非流式 chat 已返回最终答案：直接按块切片输出（模拟流式），
            # 避免同一答案再走一次 chat_stream 重复生成，节省一次完整 LLM 调用
            content = (result.content or "").strip()
            if content:
                for chunk in self._chunk_text(content):
                    yield {"type": AssistantEventType.TOKEN.mark, "content": chunk}
            else:
                # 兜底：模型未返回任何内容时尝试流式再取一次，仍为空则给友好提示
                answer_chunks: list[str] = []
                for chunk in llm_provider.chat_stream(
                    messages=cast(ChatMessage, messages),
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                ):
                    answer_chunks.append(chunk)
                    yield {"type": AssistantEventType.TOKEN.mark, "content": chunk}
                content = "".join(answer_chunks).strip()
                if not content:
                    content = ASSISTANT_EMPTY_REPLY_MESSAGE
                    yield {"type": AssistantEventType.TOKEN.mark, "content": content}
            saved = self._save_message(conversation.id, AssistantMessageRole.ASSISTANT.value, content)
            self._maybe_roll_summary(conversation)
            self._maybe_rename(conversation, query, content)
            yield self._done_event(conversation.id, saved.id)
            return
        # 达到工具步数上限仍无最终答案（异常兜底，避免死循环）
        saved = self._save_message(conversation.id, AssistantMessageRole.ASSISTANT.value, ASSISTANT_FALLBACK_MESSAGE)
        yield {"type": AssistantEventType.ERROR.mark, "message": "对话步骤超限，请重试"}
        yield self._done_event(conversation.id, saved.id)

    def _build_context(
        self,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> list[dict[str, object]]:
        """组装对话上下文（第 0/2/3 层记忆）。

        第 0 层：系统提示词（入口清单 + 用户档案 + RAG 预留位），永不丢弃
        第 2 层：滚动摘要（Conversation.summary）
        第 3 层：最近原文（保留 recent_raw_rounds 轮，按 token 预算裁剪）

        Args:
            conversation: 会话实体
            user_id: 用户ID
            query: 本轮用户输入（供 RAG 检索）

        Returns:
            list[dict[str, object]]: 上下文消息列表（调用 SDK 时 cast 为 ChatMessage）
        """
        memory_cfg = settings.ai.memory
        retriever_context = self._retrieve_context(query)
        system_prompt = self._knowledge_base.build_system_prompt(
            user_id, retriever_context=retriever_context, user_question=query
        )
        budget = max(memory_cfg.token_budget - estimate_tokens(system_prompt), 0)
        messages: list[dict[str, object]] = [{"role": "system", "content": system_prompt}]
        if conversation.summary:
            messages.append({"role": "system", "content": f"历史摘要：{conversation.summary}"})
        keep_messages = memory_cfg.recent_raw_rounds * ASSISTANT_ROLL_TRIGGER_FACTOR
        recent = self._message_repository.list_by_conversation(conversation.id, limit=keep_messages)
        raw_messages: list[dict[str, object]] = [
            {"role": entity.role, "content": entity.content} for entity in recent
        ]
        while (
            raw_messages
            and estimate_tokens(self._join_text(messages) + self._join_text(raw_messages)) > budget
        ):
            raw_messages.pop(0)
        messages.extend(raw_messages)
        return messages

    @staticmethod
    def _join_text(messages: list[dict[str, object]]) -> str:
        """将消息列表拼为纯文本用于 token 估算。

        Args:
            messages: 消息列表

        Returns:
            str: 拼接文本
        """
        return "\n".join(str(item.get("content", "")) for item in messages)

    @staticmethod
    def _chunk_text(text: str) -> Iterator[str]:
        """将完整回复按固定窗口切块，模拟流式输出体验。

        非流式 chat 已拿到完整答案时直接切片下发，避免重复调用 LLM。

        Args:
            text: 完整回复文本

        Yields:
            str: 切块后的文本片段
        """
        for index in range(0, len(text), ASSISTANT_TOKEN_CHUNK_SIZE):
            yield text[index : index + ASSISTANT_TOKEN_CHUNK_SIZE]

    def _retrieve_context(self, query: str) -> str:
        """获取检索补充知识（RAG 预留；未启用时返回空串）。

        Args:
            query: 查询文本

        Returns:
            str: 补充知识文本（空串表示无）
        """
        if not settings.ai.retriever.enabled:
            return ""
        chunks = self._retriever.retrieve(query, top_k=settings.ai.retriever.top_k)
        return "\n".join(chunk.content for chunk in chunks)

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

    def _maybe_roll_summary(self, conversation: AssistantConversationEntity) -> None:
        """第 2 层滚动摘要：窗口外旧消息渐进压缩进 summary 并删除原文。

        触发条件：消息总数超过（recent_raw_rounds × 2）；
        每次折入 ASSISTANT_ROLL_CHUNK_SIZE 条最旧消息，避免单次压缩过重。

        Args:
            conversation: 会话实体
        """
        memory_cfg = settings.ai.memory
        if not memory_cfg.enabled:
            return
        total = self._message_repository.count_by_conversation(conversation.id)
        keep_count = memory_cfg.recent_raw_rounds * ASSISTANT_ROLL_TRIGGER_FACTOR
        if total <= keep_count:
            return
        evicted = self._message_repository.list_oldest_outside_window(
            conversation.id,
            keep_count=keep_count,
            limit=ASSISTANT_ROLL_CHUNK_SIZE,
        )
        if not evicted:
            return
        chunk_text = "\n".join(f"{entity.role}: {entity.content}" for entity in evicted)
        previous = conversation.summary or ""
        combined = f"{previous}\n{chunk_text}" if previous else chunk_text
        new_summary = self._get_llm().summarize(combined)
        self._conversation_repository.update_summary(conversation.id, new_summary)
        conversation.summary = new_summary
        self._message_repository.delete_by_ids([entity.id for entity in evicted])
        self._conversation_repository.commit()
        logger.info(f"AI 助手滚动摘要：conversation={conversation.id} 折入 {len(evicted)} 条旧消息")

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
