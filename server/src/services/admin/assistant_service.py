#!/usr/bin/env python3
"""AI 助手服务：会话管理与对话入口（薄编排层）。

职责（服务层收口业务规则与事务，禁止直接操作数据库 / HTTP 对象）：
    - 会话生命周期：按用户创建 / 校验归属 / 分页查询 / 置顶 / 删除
    - 反馈：用户 👍👎 写入 assistant_feedbacks（后续提示词调优数据源）
    - 对话入口：组装上下文（MemoryFacade 四层记忆）→ 委托 agent 循环
    - SSE 通道保护：请求级超时 / 客户端断连检测 / 异常兜底
    - 轮次收尾：消息落库 + 滚动摘要 + 标题归纳（经回调端口注入 agent）
    - 跳转审计：navigate 动作写审计日志（经回调端口注入 agent）

协作模块（深度实现不在本文件）：
    - src/assistant/agent.py     agent 循环：流式推理 / 三分支决策 / 工具执行
    - src/assistant/text_call.py 正文内联工具调用的协议防御（检测门 + 解析）
    - src/assistant/memory.py    四层记忆编排（上下文组装 + 滚动摘要）

同步形态：全部 def 同步实现，由 FastAPI 同步接口在线程池中执行；
重 IO（大模型调用）使用 openai 同步客户端。
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

from src.assistant.agent import AgentStepLimitExceeded, AssistantAgent
from src.assistant.knowledge import SystemPromptBuilder
from src.assistant.memory import MemoryFacade, NullUserLongTermMemory
from src.assistant.title import generate_title
from src.assistant.tools import ToolRegistry
from src.constants.assistant import (
    ASSISTANT_ENTITY_TYPE,
    ASSISTANT_ENTRY_CATALOG,
    ASSISTANT_FALLBACK_MESSAGE,
    ASSISTANT_MESSAGE_LIST_LIMIT,
    AssistantEventType,
    AssistantMessageRole,
)
from src.core.config import settings
from src.core.exceptions import ExternalServiceException, NotFoundException
from src.core.logger import logger
from src.infras.llm import LLMProvider, get_llm_provider
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


#: 客户端断连检测间隔（秒）：节流调用 disconnect_checker，避免逐事件检测
_DISCONNECT_CHECK_INTERVAL: float = 2.0


class AssistantService:
    """AI 助手编排服务（特殊编排职责，不继承 BaseService，参考 AuthService 写法）。"""

    def __init__(
        self,
        conversation_repository: AssistantConversationRepository,
        message_repository: AssistantMessageRepository,
        feedback_repository: AssistantFeedbackRepository,
    ) -> None:
        """初始化 AI 助手服务。

        Args:
            conversation_repository: 会话仓库
            message_repository: 消息仓库
            feedback_repository: 反馈仓库
        """
        self._conversation_repository: AssistantConversationRepository = conversation_repository
        self._message_repository: AssistantMessageRepository = message_repository
        self._feedback_repository: AssistantFeedbackRepository = feedback_repository
        self._llm_provider: LLMProvider = get_llm_provider()
        self._tool_registry: ToolRegistry = self._build_default_registry()
        self._system_prompt_builder: SystemPromptBuilder = SystemPromptBuilder(NullUserLongTermMemory())
        # 记忆子系统：四层记忆统一编排（L0 委托知识库；存储端口注入仓储）
        self._memory_facade: MemoryFacade = MemoryFacade(
            system_prompt_builder=self._system_prompt_builder,
            conversation_repository=conversation_repository,
            message_repository=message_repository,
        )
        # agent 循环：流式推理 / 三分支决策 / 工具执行（写路径经回调端口委托本类方法）
        self._agent: AssistantAgent = AssistantAgent(
            llm_provider=self._llm_provider,
            tool_registry=self._tool_registry,
            finish_round=self._finish_round,
            navigate_reply_builder=self._build_navigate_reply,
            navigate_auditor=self._audit_navigate,
        )

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
        disconnect_checker: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, object]]:
        """执行一轮对话，逐事件产出 SSE 数据。

        事件类型（AssistantEventType）：
            thinking / reasoning: 思考状态 / 思维链增量
            step:                执行步骤提示（工具调用等）
            navigate / denied:   工具动作透出
            token:               回复文本增量
            error:               功能未启用 / 会话不存在 / 大模型服务异常 / 超时 / 步数超限
            done:                本轮结束（成功含 message_id；失败时 message_id 为空）

        通道级保护（在事件流外层包裹，业务异常 + 不可预期异常均在服务层兜底）：
            - 请求级超时：整轮对话（含多轮 tool call）超过
              chat_request_timeout_seconds 时主动下发 error + done 并终止；
            - 客户端断连感知：节流调用 disconnect_checker，客户端关闭页面后
              及时终止服务端生成，避免浪费大模型 token 与线程资源。

        Args:
            user: 当前用户
            conversation_id: 会话ID（为空则创建新会话）
            message: 用户输入
            operator: 操作人上下文（operator_id / operator_name / ip_address，
                由 api 层 get_user_operator_context 构造，navigate 审计落库用）
            disconnect_checker: 客户端断连检测回调（由 api 层注入，返回 True
                表示已断开）；service 层不持有 Request 对象，通过回调解耦

        Yields:
            dict[str, object]: SSE 事件字典
        """
        if not settings.ai.enabled:
            yield {"type": AssistantEventType.ERROR.mark, "message": "AI 助手功能未启用，请在配置中开启"}
            yield {"type": AssistantEventType.DONE.mark, "conversation_id": conversation_id, "message_id": None}
            return
        conversation: AssistantConversationEntity | None = None

        try:
            # 1. 保存会话和用户输入消息
            conversation = self._get_or_create_conversation(user.id, conversation_id)
            self._save_message(conversation.id, AssistantMessageRole.USER.value, message)

            # 2. 组装上下文（四层记忆）并委托 agent 循环 + 通道级保护（超时/断连/异常兜底）
            messages = self._memory_facade.build_context(conversation, user.id, message)
            messages.append({"role": "user", "content": message})
            yield from self._stream_with_protection(
                self._agent.run(conversation, user, message, messages, operator),
                conversation_id=conversation.id,
                disconnect_checker=disconnect_checker,
            )
        except NotFoundException as exc:
            # 会话不存在或归属不符：不落库，直接提示并结束
            yield {"type": AssistantEventType.ERROR.mark, "message": str(exc)}
            yield {"type": AssistantEventType.DONE.mark, "conversation_id": conversation_id, "message_id": None}
        except AgentStepLimitExceeded as exc:
            # agent 循环步数超限：落兜底消息并提示重试（与下方外部异常同一收尾形态）
            logger.warning(f"AI 助手对话步数超限：conversation={exc.conversation_id}")
            saved = self._save_message(
                exc.conversation_id, AssistantMessageRole.ASSISTANT.value, ASSISTANT_FALLBACK_MESSAGE
            )
            yield {"type": AssistantEventType.ERROR.mark, "message": "对话步骤超限，请重试"}
            yield self._done_event(exc.conversation_id, saved.id)
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

    def _stream_with_protection(
        self,
        event_stream: Iterator[dict[str, object]],
        conversation_id: int,
        disconnect_checker: Callable[[], bool] | None,
    ) -> Iterator[dict[str, object]]:
        """SSE 通道保护：超时检测 + 客户端断连检测 + 不可预期异常兜底。

        在 agent 事件流外层包裹，逐事件检查：
            1. 请求级超时：超过 chat_request_timeout_seconds 时下发 error + done；
            2. 客户端断连：节流调用 disconnect_checker，命中则静默终止；
            3. 不可预期异常：兜底为 error + done，防止流中断无响应。

        Args:
            event_stream: agent 事件流（AssistantAgent.run 产出）
            conversation_id: 会话ID（超时/异常事件需要）
            disconnect_checker: 客户端断连检测回调（None 表示不检测）

        Yields:
            dict[str, object]: SSE 事件字典
        """
        start_time = time.monotonic()
        request_timeout = settings.ai.llm.chat_request_timeout_seconds
        last_disconnect_check = 0.0
        try:
            for event in event_stream:
                now = time.monotonic()
                # 1. 请求级超时：在事件边界检查，超时则主动结束
                if now - start_time > request_timeout:
                    logger.warning(
                        f"AI 助手对话超时（>{request_timeout}s），主动终止；"
                        f"conversation={conversation_id}"
                    )
                    yield {
                        "type": AssistantEventType.ERROR.mark,
                        "message": "AI 助手响应超时，请稍后重试",
                    }
                    yield {
                        "type": AssistantEventType.DONE.mark,
                        "conversation_id": conversation_id,
                        "message_id": None,
                    }
                    return

                # 2. 客户端断连：节流检测，命中则静默终止（客户端已收不到事件）
                if (
                    disconnect_checker is not None
                    and now - last_disconnect_check >= _DISCONNECT_CHECK_INTERVAL
                ):
                    last_disconnect_check = now
                    if disconnect_checker():
                        logger.info(
                            f"AI 助手客户端已断开，终止对话流；"
                            f"conversation={conversation_id}"
                        )
                        return
                yield event
        except Exception as exc:  # noqa: BLE001 - SSE 通道最后防线，仅兜底不可预期异常
            logger.error(f"AI 助手 SSE 通道异常: {exc}")
            yield {
                "type": AssistantEventType.ERROR.mark,
                "message": AssistantEventType.ERROR.desc,
            }
            yield {
                "type": AssistantEventType.DONE.mark,
                "conversation_id": conversation_id,
                "message_id": None,
            }

    # ── 内部实现 ───────────────────────────────────────────────

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
        self._memory_facade.roll_summary(conversation)
        self._maybe_rename(conversation, query, content)
        yield self._done_event(conversation.id, saved.id)

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
        hit = self._memory_facade.system_prompt_builder.match_faq(query)
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
                self._llm_provider,
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
