#!/usr/bin/env python3
"""记忆分层：第 1 层长期记忆预留接口。

记忆分层（第 0/1/2/3 层）：
    第 0 层 · 系统提示词   永不丢弃，固定预算（knowledge.KnowledgeBase 维护）
    第 1 层 · 长期记忆     跨会话用户档案（user_profile）——【当前不实现，仅预留接口】
    第 2 层 · 滚动摘要     窗口外旧消息渐进压缩（Conversation.summary，assistant_service 维护）
    第 3 层 · 最近 N 轮原文 精确保留最近几轮（assistant_service.build_context 维护）

本文件只负责第 1 层长期记忆的接口预留：上层（knowledge 提示词组装）通过
UserMemoryProvider 注入用户档案文本，接入时替换实现即可，无需改动上层。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class UserMemoryProvider(ABC):
    """用户长期记忆提供者（第 1 层抽象接口）。

    后续接入方式：
        1. 新增 user_profile 表（用户长期偏好 / 关注点）
        2. 实现子类读取该表并返回档案文本
        3. 替换依赖工厂中的 NullUserMemory 为真实实现
    """

    @abstractmethod
    def load_user_context(self, user_id: int) -> str:
        """返回注入系统提示词的『用户档案』文本。

        Args:
            user_id: 用户ID

        Returns:
            str: 档案文本；未接入长期记忆时返回空串
        """


class NullUserMemory(UserMemoryProvider):
    """长期记忆空实现（占位）。

    第 1 层未启用时使用，返回空串，保证上层提示词组装逻辑不变。
    """

    def load_user_context(self, user_id: int) -> str:
        return ""
