#!/usr/bin/env python3
"""静态知识库：系统提示词与入口清单组装。

职责：
    - 将系统入口清单（ASSISTANT_ENTRY_CATALOG）与用户档案（记忆第 1 层注入点）
      组装为系统提示词，注入对话上下文
    - 入口清单当前来自常量（P0 静态维护）；后续可替换为从菜单表动态生成，
      本类只依赖入口数据源，替换数据源不影响上层

说明：
    - 不引入 RAG：知识以提示词注入为主；retriever_context 参数预留 RAG 注入位
    - 用户档案通过 UserMemoryProvider 注入（第 1 层长期记忆，当前为空实现）
"""

from __future__ import annotations

from src.assistant.memory import UserMemoryProvider
from src.constants.assistant import ASSISTANT_ENTRY_CATALOG


class KnowledgeBase:
    """系统提示词组装器。

    Attributes:
        _user_memory: 用户长期记忆提供者（第 1 层注入点）
    """

    def __init__(self, user_memory: UserMemoryProvider) -> None:
        """初始化知识库。

        Args:
            user_memory: 用户长期记忆提供者
        """
        self._user_memory: UserMemoryProvider = user_memory

    def build_system_prompt(self, user_id: int, retriever_context: str = "") -> str:
        """组装系统提示词。

        Args:
            user_id: 当前用户ID（用于注入用户档案）
            retriever_context: 检索补充知识（RAG 预留，未启用时为空串）

        Returns:
            str: 完整系统提示词
        """
        entries_block = "\n".join(
            f"- {item['title']}（{item['path']}）：{item['description']}"
            for item in ASSISTANT_ENTRY_CATALOG
        )
        user_context = self._user_memory.load_user_context(user_id)
        user_block = user_context if user_context else "（暂无，按通用规则回答）"
        rag_block = f"\n【补充知识】\n{retriever_context}" if retriever_context else ""
        return (
            "你是「汉江管理系统」的 AI 导览助手，帮助不熟悉系统的用户解答用法、"
            "引导跳转到正确入口。\n"
            "【用户使用引导】用户刚接触系统时不知道能问什么，请主动展示能力：\n"
            "1. 用户问『你能干什么 / 这个系统怎么用』时，直接列出典型问法示例，例如：\n"
            "   · 怎么添加用户？\n"
            "   · 帮我跳到权限管理\n"
            "   · 用户列表在哪里？\n"
            "   · 怎么修改我的个人资料？\n"
            "2. 回答开头先给结论或操作步骤，结尾可自然带一句下一步建议"
            "（如『需要我帮你跳过去吗？』），引导用户继续使用；\n"
            f"【系统入口（只能推荐当前用户有权限访问的）】\n{entries_block}\n"
            f"【用户档案】{user_block}\n"
            "【硬约束】\n"
            "1. 回答简洁，直接给出操作步骤；\n"
            "2. 需要跳转时调用 navigate 工具，绝不虚构入口；\n"
            "3. 不确定就明说『我不确定』，禁止编造功能；\n"
            "4. 只能推荐当前用户有权限的入口。"
            f"{rag_block}"
        )
