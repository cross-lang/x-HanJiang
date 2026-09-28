#!/usr/bin/env python3
"""
通知接收人数据访问实现
本模块提供通知接收人 Repository 的 SQLAlchemy 数据库实现，
负责个人通知接收人的查询、创建、更新与删除。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    越权校验（接收人必须属于当前用户）与业务规则由 Service 层完成。

Classes:
    NotificationRecipientRepository: 通知接收人数据访问 SQLAlchemy 实现
"""

from sqlalchemy import select

from src.models.entities.notification_recipient_entity import NotificationRecipientEntity
from src.repositories.base_repository import BaseRepository


class NotificationRecipientRepository(BaseRepository[NotificationRecipientEntity, int]):
    """通知接收人数据访问 SQLAlchemy 实现。"""

    model_class = NotificationRecipientEntity

    def list_by_user(self, user_id: int) -> list[NotificationRecipientEntity]:
        """查询指定用户的全部通知接收人（按渠道与主键排序）。"""
        stmt = (
            select(NotificationRecipientEntity)
            .where(NotificationRecipientEntity.user_id == user_id)
            .order_by(NotificationRecipientEntity.channel, NotificationRecipientEntity.id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_id_and_user(self, recipient_id: int, user_id: int) -> NotificationRecipientEntity | None:
        """按主键 + 归属用户查询单条接收人（用于越权校验）。"""
        stmt = select(NotificationRecipientEntity).where(
            NotificationRecipientEntity.id == recipient_id,
            NotificationRecipientEntity.user_id == user_id,
        )
        return self.session.execute(stmt).scalars().first()
