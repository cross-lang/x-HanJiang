#!/usr/bin/env python3
"""L0 系统提示词层：适配 SystemPromptBuilder 的纯渲染层。"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from src.assistant.memories.base import MemoryContext, MemoryLayer
from src.utils.text import estimate_tokens

if TYPE_CHECKING:
    from src.assistant.memories.knowledge import SystemPromptBuilder
    from src.models.entities.assistant_entity import AssistantConversationEntity


class SystemPromptLayer(MemoryLayer):
    """第 0 层：系统提示词（最高优先级，永不丢弃）。

    作为 MemoryLayer 与 SystemPromptBuilder 之间的纯渲染适配器：提示词的
    静态内容（身份 / 系统入口路由表 / FAQ）由 SystemPromptBuilder 渲染，本轮两个
    动态内容源——L1 用户档案与 RAG 补充知识——不再由本层主动拉取，而是由
    MemoryFacade 在驱动各层之前取好，经 ctx.user_context /
    ctx.retriever_context 注入；本层只读 ctx 并调用渲染、纳入预算记账。

    这样 L0 与 L1 长期记忆 / RAG 检索彻底解耦：L0 不持有 retriever /
    user_long_term_memory 引用，新增 / 替换 L1 或 RAG 实现时 L0 零改动。

    流程：
        1. 从 ctx 读取 MemoryFacade 预先注入的用户档案与检索补充知识；
        2. 委托 SystemPromptBuilder 组装完整系统提示词（按用户权限过滤系统入口路由表）；
        3. 向 ctx 追加该 system 消息并按实际 token 扣减预算。

    不变式：
        - 每轮恰好注入 1 条 role="system" 的消息；
        - 作为第一个执行的层（order=0），其 charge 决定 L2/L3 的可用预算；
        - 不读取 conversation、不写库、不调用 L1 / RAG（纯只读 ctx + 渲染）；
        - 即便 remaining_budget=0 也照常注入：L0 优先级最高，预算缺口由
          后面的 L3「少带原文」来吸收，而不是压缩提示词本身。
    """

    order: ClassVar[int] = 0

    def __init__(
        self,
        system_prompt_builder: SystemPromptBuilder,
    ) -> None:
        """初始化第 0 层。

        Args:
            system_prompt_builder: 系统提示词组装器（纯静态渲染）
        """
        self._system_prompt_builder: SystemPromptBuilder = system_prompt_builder

    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """组装并注入系统提示词。

        L1 用户档案与 RAG 补充知识由 MemoryFacade 预先写入 ctx，本层直接读取，
        不再持有 L1 / RAG 引用，也不再自行检索。

        Args:
            ctx: 层间编排上下文（含 user_context / retriever_context /
                user_permissions，均由 Facade 在层循环前写定）
            conversation: 会话实体（本层不使用，保持接口一致）
            user_id: 当前用户ID（本层不使用，保持接口一致）
            query: 本轮用户输入（FAQ 命中用）
        """
        # 委托 SystemPromptBuilder 组装完整系统提示词（按用户权限过滤系统入口路由表）
        system_prompt = self._system_prompt_builder.build_system_prompt(
            user_context=ctx.user_context,
            retriever_context=ctx.retriever_context,
            user_question=query,
            user_permissions=ctx.user_permissions,
        )

        # 向 ctx 追加该 system 消息并按实际 token 扣减预算
        ctx.append("system", system_prompt)
        ctx.charge(estimate_tokens(system_prompt))
