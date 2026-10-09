#!/usr/bin/env python3
"""L3 最近原文层：剩余预算内反向贪心保留最近对话原文。"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from src.assistant.memories.base import MemoryContext, MemoryLayer
from src.assistant.memories.ports import MessageRepository
from src.constants.assistant import ASSISTANT_ROLL_TRIGGER_FACTOR
from src.core.config import settings
from src.utils.text import estimate_tokens

if TYPE_CHECKING:
    from src.models.entities.assistant_entity import AssistantConversationEntity


class RecentMemoryLayer(MemoryLayer):
    """第 3 层：最近原文（最低优先级，超预算从最旧一条开始丢弃）。

    职责：
        取出最近窗口（recent_raw_rounds × 因子条）内的原文，在
        ctx.remaining_budget 额度内从「最新一条 → 更旧」反向贪心选取，
        再 reverse 回时间正序后并入上下文。

    选取策略的两个关键决策：
        - 遇到第一条装不下的消息立即 break，而不是跳过它去试更旧、更短的：
          近因连贯性比「硬凑条数」更重要，不能用一条更旧的短消息替换掉
          紧邻本轮的新消息，否则对话语境断裂；
        - 选完不调用 charge：本层是最后一个消费者，预算只用于决定「保留
          多少」，之后没有其他层需要读剩余预算，扣减没有意义。

    不变式：
        - 注入的消息严格保持原时间正序（最新的在最后、紧邻本轮用户消息）；
        - 可能注入 0 条（预算被 L0/L2 占满，或连最新一条都放不下）；
        - 纯只读 + ctx.messages 写入，不写库、不修改 remaining_budget。
    """

    order: ClassVar[int] = 3

    def __init__(self, message_repository: MessageRepository) -> None:
        """初始化第 3 层。

        Args:
            message_repository: 消息存储端口
        """
        self._message_repository: MessageRepository = message_repository

    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """在剩余预算内注入最近原文（时间越近越优先保留）。

        存储端口按时间正序返回「最近 limit 条」，故从最新一条反向贪心累加：
        每条消息仅估算一次（O(n)），优先保住紧邻本轮的对话上下文。

        Args:
            ctx: 层间编排上下文（remaining_budget 即 L3 可用额度）
            conversation: 会话实体
            user_id: 当前用户ID（本层不使用，保持接口一致）
            query: 本轮用户输入（本层不使用，保持接口一致）
        """
        memory_cfg = settings.ai.memory
        keep_count = memory_cfg.recent_raw_rounds * ASSISTANT_ROLL_TRIGGER_FACTOR
        recent = self._message_repository.list_by_conversation(conversation.id, limit=keep_count)
        recent_messages: list[dict[str, object]] = []
        used_tokens = 0
        for entity in reversed(recent):
            msg_tokens = estimate_tokens(entity.content)
            if used_tokens + msg_tokens > ctx.remaining_budget:
                break
            used_tokens += msg_tokens
            recent_messages.append({"role": entity.role, "content": entity.content})
        recent_messages.reverse()
        ctx.messages.extend(recent_messages)
