#!/usr/bin/env python3
"""记忆门面：编排各记忆层（自身不写记忆逻辑）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.assistant.memories.base import MemoryContext, MemoryLayer
from src.assistant.memories.long_term import NullUserLongTermMemory, UserLongTermMemory
from src.assistant.memories.ports import ConversationRepository, MessageRepository
from src.assistant.memories.recent import RecentMemoryLayer
from src.assistant.memories.summary import SummaryMemoryLayer
from src.assistant.memories.system_prompt import SystemPromptLayer
from src.assistant.retriever import RetrieverProvider, get_retriever_provider
from src.core.config import settings
from src.infras.llm import LLMProvider, get_llm_provider

if TYPE_CHECKING:
    from src.assistant.memories.knowledge import SystemPromptBuilder
    from src.models.entities.assistant_entity import AssistantConversationEntity


class MemoryFacade:
    """记忆系统编排器（Facade）：持有有序记忆层并统一驱动。

    职责：
        - build_context：先取 L1 用户档案与 RAG 补充知识写入 ctx，再按
          L0 → L2 → L3 顺序遍历各层 contribute（L0 只读 ctx 渲染，不感知 L1/RAG）
        - roll_summary：委托第 2 层 consolidate 执行压缩
        - consolidate_user_profile：委托 L1 抽取用户档案

    Attributes:
        _layers: 按注入优先级排序的记忆层列表（L0 / L2 / L3）
        _user_long_term_memory: L1 用户长期记忆提供者（读路径喂给 L0，写路径供对话结束抽取）
        _retriever: RAG 检索提供者（按开关检索补充知识，未启用时返回空串）

    生命周期与不变式：
        - 「层实例」长生命周期、可跨多轮复用：层的依赖（端口 / 适配器）
          在构造时固定，层自身不在 contribute 中累积跨轮状态；
        - 「MemoryContext」每轮一次性：build_context 每次新建 ctx，组装完
          即丢弃，杜绝上一轮消息/预算泄漏到下一轮；
        - _layers 在装配后不再变更（顺序即优先级），Facade 不做动态排序；
        - roll_summary 只做转发，不在此处判断是否该压缩——触发条件、取数、
          提交全部内聚在 L2.consolidate，保持 Facade 轻薄。
    """

    def __init__(
        self,
        system_prompt_builder: SystemPromptBuilder,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        user_long_term_memory: UserLongTermMemory | None = None,
        retriever: RetrieverProvider | None = None,
        llm_provider_getter: Callable[[], LLMProvider] | None = None,
    ) -> None:
        """初始化记忆编排器并装配各记忆层。

        Args:
            system_prompt_builder: L0 系统提示词组装器（纯静态渲染）
            conversation_repository: 会话存储端口
            message_repository: 消息存储端口
            user_long_term_memory: L1 用户长期记忆提供者（缺省使用空实现）
            retriever: RAG 检索提供者（缺省按配置工厂创建）
            llm_provider_getter: LLM 获取器（缺省使用全局懒加载工厂）
        """
        self.system_prompt_builder: SystemPromptBuilder = system_prompt_builder
        self._user_long_term_memory: UserLongTermMemory = user_long_term_memory or NullUserLongTermMemory()
        self._retriever: RetrieverProvider = retriever or get_retriever_provider()
        self.layers: tuple[MemoryLayer] = (
            # L0 系统提示词层（纯渲染：从 ctx 读取 L1/RAG 内容，不持有 L1/RAG 引用）
            SystemPromptLayer(self.system_prompt_builder),
            # L2 滚动摘要层
            SummaryMemoryLayer(conversation_repository, message_repository, llm_provider_getter or get_llm_provider),
            # L3 最近原文层
            RecentMemoryLayer(message_repository),
        )

    def build_context(
        self,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
        user_permissions: set[str] | None = None,
    ) -> list[dict[str, object]]:
        """组装本轮对话上下文：先取 L1/RAG 写入 ctx，再遍历各层贡献记忆。

        L1 用户档案与 RAG 补充知识是「本轮动态内容」，由本编排器在驱动
        各层之前统一取好并写入 ctx.user_context / ctx.retriever_context。
        这样 L0 只读 ctx 渲染，不再持有 L1 / RAG 引用——L1 / RAG 的新增
        或替换只影响本编排器，L0 零改动。

        Args:
            conversation: 会话实体
            user_id: 当前用户ID
            query: 本轮用户输入
            user_permissions: 当前用户权限码集合（L0 据此过滤系统入口路由表；
                None 表示不传入，L0 不过滤；含 "*" 表示超级管理员通配）

        Returns:
            list[dict[str, object]]: 上下文消息列表（调用 SDK 时 cast 为 ChatMessage）
        """
        ctx = MemoryContext(
            remaining_budget=settings.ai.memory.token_budget,
            user_permissions=user_permissions or set(),
        )
        # 1. 取用户档案
        ctx.user_context = self._user_long_term_memory.load_user_context(user_id)
        # 2. 取 RAG 补充知识
        ctx.retriever_context = self._retrieve_context(query)
        # 3. 按 L0 → L2 → L3 顺序驱动各层（L0 直接读 ctx，不自行拉取）
        for layer in self.layers:
            layer.contribute(ctx, conversation, user_id, query)
        return ctx.messages

    def _retrieve_context(self, query: str) -> str:
        """动态检索外部补充知识（RAG；未启用时返回空串）。

        Args:
            query: 查询文本

        Returns:
            str: 补充知识文本（空串表示无）
        """
        if not settings.ai.retriever.enabled:
            return ""
        chunks = self._retriever.retrieve(query, top_k=settings.ai.retriever.top_k)
        return "\n".join(chunk.content for chunk in chunks)

    def roll_summary(self, conversation: AssistantConversationEntity) -> None:
        """第 2 层压缩入口（对话结束后调用）。

        Args:
            conversation: 会话实体
        """
        summary_layer: SummaryMemoryLayer = self.layers[1]
        summary_layer.consolidate(conversation)

    def consolidate_user_profile(self, user_id: int, conversation_id: int) -> None:
        """第 1 层档案抽取入口（对话结束后调用）。

        Args:
            user_id: 用户ID
            conversation_id: 会话ID
        """
        self._user_long_term_memory.consolidate(user_id, conversation_id)
