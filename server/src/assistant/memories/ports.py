#!/usr/bin/env python3
"""记忆系统存储端口（Ports）：只定义契约，不提供实现。

四个 Protocol 类只声明方法签名 / 字段：
    - Message：消息记录的最小结构契约（ORM 实体结构化满足）
    - MessageRepository / ConversationRepository / UserProfileRepository：存储端口

实际干活的实现方在 repositories/assistant_repository.py，
只要方法签名匹配即被认可为满足契约（结构化子类型），无需显式继承。
这样记忆各层不认识 SQLAlchemy，可被内存 fake 轻松替换，便于单测。
"""

from __future__ import annotations

from typing import Protocol


class Message(Protocol):
    """消息记录最小结构契约（ORM 实体 AssistantMessageEntity 结构化满足）。"""

    id: int
    role: str
    content: str


class MessageRepository(Protocol):
    """消息存储端口（契约）：声明消息读写能力，实现方在 repositories/assistant_repository.py。"""

    def list_by_conversation(
        self, conversation_id: int, limit: int = 100
    ) -> list[Message]:
        """按时间正序返回会话最近 limit 条消息。"""

    def count_by_conversation(self, conversation_id: int) -> int:
        """统计会话消息总数。"""

    def list_oldest_outside_window(
        self,
        conversation_id: int,
        keep_count: int,
        limit: int = 10,
    ) -> list[Message]:
        """跳过最近 keep_count 条，按时间正序返回最旧的 limit 条。"""

    def delete_by_ids(self, message_ids: list[int]) -> None:
        """按主键批量删除已折入摘要的旧消息。"""


class ConversationRepository(Protocol):
    """会话存储端口（契约）：声明摘要持久化能力，实现方在 repositories/assistant_repository.py。"""

    def update_summary(self, conversation_id: int, summary: str) -> None:
        """更新会话滚动摘要。"""

    def commit(self) -> None:
        """提交事务（提交权归属服务/记忆边界，仓储只 flush）。"""


class UserProfileRepository(Protocol):
    """用户档案存储端口（契约）：声明档案读写能力，实现方在 repositories/assistant_repository.py。"""

    def get_by_user(self, user_id: int) -> object | None:
        """按用户ID查询档案记录；返回含 profile / version 属性的对象，不存在返回 None。"""

    def upsert(self, user_id: int, profile: str, version: int) -> None:
        """写入或更新用户档案（带乐观锁）。"""
