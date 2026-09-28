#!/usr/bin/env python3
"""AI 助手数据访问层。

职责：封装会话、消息、反馈的查询与写入，隔离底层存储细节。
约束：
    - 仅允许依赖 models/ 与 infras/ 层，禁止导入 services / api / schemas
    - 不做业务判断，只做数据操作；返回值仅返回 ORM 实体或基础数据类型
    - 不抛业务异常；数据库异常由基类统一转换为 DatabaseException
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, desc, func, select

from src.models.entities.assistant_entity import (
    AssistantConversationEntity,
    AssistantFeedbackEntity,
    AssistantMessageEntity,
)
from src.repositories.base_repository import BaseRepository


class AssistantConversationRepository(BaseRepository[AssistantConversationEntity, int]):
    """会话仓库。"""

    model_class = AssistantConversationEntity

    def get_by_id(self, entity_id: int) -> AssistantConversationEntity | None:
        """按ID查询未软删除的会话。

        Args:
            entity_id: 会话ID

        Returns:
            AssistantConversationEntity | None: 会话实体；不存在或已软删除返回 None
        """
        stmt = select(self.model_class).where(
            self.model_class.id == entity_id,
            self.model_class.deleted_at.is_(None),
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_user(self, user_id: int, limit: int = 20) -> list[AssistantConversationEntity]:
        """查询指定用户未软删除的会话列表（置顶优先，同组内按更新时间倒序）。

        Args:
            user_id: 用户ID
            limit: 返回条数上限

        Returns:
            list[AssistantConversationEntity]: 会话实体列表
        """
        stmt = (
            select(self.model_class)
            .where(
                self.model_class.user_id == user_id,
                self.model_class.deleted_at.is_(None),
            )
            .order_by(
                desc(self.model_class.is_pinned),
                desc(self.model_class.updated_at),
            )
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def soft_delete(self, conversation_id: int) -> None:
        """软删除会话（deleted_at 置当前时间，消息与反馈物理保留留档）。

        Args:
            conversation_id: 会话ID
        """
        entity = self.get_by_id(conversation_id)
        if entity is None:
            return
        entity.deleted_at = datetime.now()
        self.session.flush()

    def update_pinned(self, conversation_id: int, pinned: bool) -> None:
        """设置会话置顶状态。

        Args:
            conversation_id: 会话ID
            pinned: True 置顶 / False 取消置顶
        """
        entity = self.get_by_id(conversation_id)
        if entity is None:
            return
        entity.is_pinned = pinned
        self.session.flush()

    def update_summary(self, conversation_id: int, summary: str) -> None:
        """更新会话滚动摘要（第 2 层记忆）。

        Args:
            conversation_id: 会话ID
            summary: 新的滚动摘要内容
        """
        entity = self.get_by_id(conversation_id)
        if entity is None:
            return
        entity.summary = summary
        self.session.flush()


class AssistantMessageRepository(BaseRepository[AssistantMessageEntity, int]):
    """会话消息仓库。"""

    model_class = AssistantMessageEntity

    def add_message(self, conversation_id: int, role: str, content: str) -> AssistantMessageEntity:
        """追加一条会话消息。

        Args:
            conversation_id: 会话ID
            role: 消息角色（user / assistant）
            content: 消息内容

        Returns:
            AssistantMessageEntity: 新建的消息实体
        """
        entity = self.model_class(conversation_id=conversation_id, role=role, content=content)
        return self.create(entity)

    def list_by_conversation(
        self,
        conversation_id: int,
        limit: int = 100,
    ) -> list[AssistantMessageEntity]:
        """查询会话消息（按创建时间正序，仅返回最近 limit 条）。

        Args:
            conversation_id: 会话ID
            limit: 返回条数上限

        Returns:
            list[AssistantMessageEntity]: 消息实体列表（时间正序）
        """
        stmt = (
            select(self.model_class)
            .where(self.model_class.conversation_id == conversation_id)
            .order_by(desc(self.model_class.created_at), desc(self.model_class.id))
            .limit(limit)
        )
        rows = list(self.session.execute(stmt).scalars().all())
        rows.reverse()
        return rows

    def count_by_conversation(self, conversation_id: int) -> int:
        """统计会话消息总数。

        Args:
            conversation_id: 会话ID

        Returns:
            int: 消息条数
        """
        stmt = select(func.count()).select_from(self.model_class).where(
            self.model_class.conversation_id == conversation_id
        )
        return int(self.session.execute(stmt).scalar() or 0)

    def list_oldest_outside_window(
        self,
        conversation_id: int,
        keep_count: int,
        limit: int = 10,
    ) -> list[AssistantMessageEntity]:
        """查询滚动窗口之外的最旧消息（第 2 层记忆压缩的候选块）。

        说明：按时间正序，跳过最近 keep_count 条，返回最旧的 limit 条。

        Args:
            conversation_id: 会话ID
            keep_count: 保留的最近消息条数（窗口）
            limit: 返回条数上限

        Returns:
            list[AssistantMessageEntity]: 窗口外最旧消息（时间正序）
        """
        stmt = (
            select(self.model_class)
            .where(self.model_class.conversation_id == conversation_id)
            .order_by(self.model_class.created_at.asc(), self.model_class.id.asc())
            .offset(keep_count)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def delete_by_ids(self, message_ids: list[int]) -> None:
        """按主键批量删除消息（已折入摘要的旧消息）。

        Args:
            message_ids: 待删除的消息主键列表
        """
        if not message_ids:
            return
        stmt = delete(self.model_class).where(self.model_class.id.in_(message_ids))
        self.session.execute(stmt)
        self.session.flush()


class AssistantFeedbackRepository(BaseRepository[AssistantFeedbackEntity, int]):
    """消息反馈仓库。"""

    model_class = AssistantFeedbackEntity

    def add_feedback(
        self,
        conversation_id: int,
        message_id: int,
        user_id: int,
        positive: bool,
        comment: str | None,
    ) -> AssistantFeedbackEntity:
        """记录一条消息反馈。

        Args:
            conversation_id: 会话ID
            message_id: 被反馈的消息ID
            user_id: 反馈用户ID
            positive: 是否好评
            comment: 补充意见（可空）

        Returns:
            AssistantFeedbackEntity: 新建的反馈实体
        """
        entity = self.model_class(
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            positive=positive,
            comment=comment,
        )
        return self.create(entity)
