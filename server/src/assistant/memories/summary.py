#!/usr/bin/env python3
"""L2 滚动摘要层：窗口外历史的压缩记忆（读取注入 + 压缩沉淀）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from src.assistant.memories.base import MemoryContext, MemoryLayer
from src.assistant.memories.ports import ConversationRepository, MessageRepository
from src.constants.assistant import (
    ASSISTANT_ROLL_CHUNK_SIZE,
    ASSISTANT_ROLL_TRIGGER_FACTOR,
)
from src.core.config import settings
from src.core.logger import logger
from src.infras.llm import LLMProvider, get_llm_provider
from src.utils.text import estimate_tokens

if TYPE_CHECKING:
    from src.models.entities.assistant_entity import AssistantConversationEntity


class SummaryMemoryLayer(MemoryLayer):
    """第 2 层：滚动摘要（窗口外历史的压缩记忆，整体保留）。

    本层是唯一同时拥有「读路径」与「写路径」的层：
        - 读路径 contribute（实现统一接口）：把已有摘要作为一条 system
          消息注入上下文，属于组装阶段，只读不写；
        - 写路径 consolidate（本层特有，不在 MemoryLayer 接口内）：对话
          结束后由 MemoryFacade 调用，把窗口外最旧消息经 LLM 压缩进 summary、
          删除原文并提交，是记忆从 L3「沉淀」到 L2 的反向操作。

    职责：
        contribute —— 有摘要注入「历史摘要：…」，无摘要则完全跳过；
        consolidate —— 统计总数 → 取窗口外最旧的一块 → 与旧摘要拼接后
                       summarize → 更新摘要、删除原文、commit。

    不变式：
        - 摘要整体保留：要么注入完整摘要、要么不注入，不对摘要做局部裁剪
          （压缩发生在 consolidate，而不是组装时）；
        - 分批折入：每次只处理 ASSISTANT_ROLL_CHUNK_SIZE 条，避免单次
          prompt 过长 / LLM 负担过重，靠多轮对话渐进压缩；
        - consolidate 成功后，内存对象 conversation.summary 与库中字段
          保持一致，且被删原文与新增摘要在同一事务内提交。

    层间关系：在 L0 之后、L3 之前执行，其 charge 会进一步缩小 L3 额度。
    """

    order: ClassVar[int] = 2

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        llm_provider_getter: Callable[[], LLMProvider],
    ) -> None:
        """初始化第 2 层。

        Args:
            conversation_repository: 会话存储端口（摘要持久化 + 提交）
            message_repository: 消息存储端口（压缩时取/删旧消息）
            llm_provider_getter: LLM 获取器（summarize 调用，懒加载）
        """
        self._conversation_repository: ConversationRepository = conversation_repository
        self._message_repository: MessageRepository = message_repository
        self._get_llm: Callable[[], LLMProvider] = llm_provider_getter

    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """注入历史摘要消息（无摘要时跳过）。

        Args:
            ctx: 层间编排上下文
            conversation: 会话实体（摘要来源）
            user_id: 当前用户ID（本层不使用，保持接口一致）
            query: 本轮用户输入（本层不使用，保持接口一致）
        """
        if not conversation.summary:
            return
        content = f"历史摘要：{conversation.summary}"
        ctx.append("system", content)
        ctx.charge(estimate_tokens(content))

    def consolidate(self, conversation: AssistantConversationEntity) -> None:
        """滚动摘要压缩：窗口外旧消息渐进折入 summary 并删除原文。

        触发条件：记忆开关开启且消息总数超过（recent_raw_rounds × 2）；
        每次折入 ASSISTANT_ROLL_CHUNK_SIZE 条最旧消息，避免单次压缩过重。

        Args:
            conversation: 会话实体
        """
        memory_cfg = settings.ai.memory
        # 1. 前置检查：记忆开关 + 消息数是否超过保留窗口
        if not memory_cfg.enabled:
            return
        total = self._message_repository.count_by_conversation(conversation.id)
        keep_count = memory_cfg.recent_raw_rounds * ASSISTANT_ROLL_TRIGGER_FACTOR
        if total <= keep_count:
            return
        # 2. 取窗口外最旧的一块（ASSISTANT_ROLL_CHUNK_SIZE 条）
        evicted = self._message_repository.list_oldest_outside_window(
            conversation.id,
            keep_count=keep_count,
            limit=ASSISTANT_ROLL_CHUNK_SIZE,
        )
        if not evicted:
            return
        # 3. 拼接待压缩文本：旧摘要 + 本批窗口外消息
        chunk_text = "\n".join(f"{entity.role}: {entity.content}" for entity in evicted)
        previous = conversation.summary or ""
        combined = f"{previous}\n{chunk_text}" if previous else chunk_text
        # 4. 调 LLM 压缩，得到新摘要
        new_summary = self._get_llm().summarize(combined)
        # 5. 持久化 + 清理：更新摘要 → 同步内存对象 → 删除已折原文 → 提交
        self._conversation_repository.update_summary(conversation.id, new_summary)
        conversation.summary = new_summary
        self._message_repository.delete_by_ids([entity.id for entity in evicted])
        self._conversation_repository.commit()
        logger.info(f"AI 助手滚动摘要：conversation={conversation.id} 折入 {len(evicted)} 条旧消息")
