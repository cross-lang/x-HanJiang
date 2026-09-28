#!/usr/bin/env python3
"""
用户通知偏好数据访问实现
本模块提供用户通知偏好 Repository 的 SQLAlchemy 数据库实现，
负责通知偏好的查询与 upsert（按 用户 + 事件 + 渠道 唯一键）。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    偏好默认值等业务规则由 Service 层完成。

Classes:
    NotificationPreferenceRepository: 用户通知偏好数据访问 SQLAlchemy 实现
"""

from sqlalchemy import select

from src.models.entities.notification_preference_entity import UserNotificationPreferenceEntity
from src.repositories.base_repository import BaseRepository


class NotificationPreferenceRepository(BaseRepository[UserNotificationPreferenceEntity, int]):
    """用户通知偏好数据访问 SQLAlchemy 实现。"""

    model_class = UserNotificationPreferenceEntity

    def list_by_user(self, user_id: int) -> list[UserNotificationPreferenceEntity]:
        """查询指定用户的全部通知偏好。"""
        stmt = select(UserNotificationPreferenceEntity).where(UserNotificationPreferenceEntity.user_id == user_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_user_event_channel(
        self,
        user_id: int,
        event_type: str,
        channel: str,
    ) -> UserNotificationPreferenceEntity | None:
        """按 用户 + 事件 + 渠道 唯一键查询单条偏好。"""
        stmt = select(UserNotificationPreferenceEntity).where(
            UserNotificationPreferenceEntity.user_id == user_id,
            UserNotificationPreferenceEntity.event_type == event_type,
            UserNotificationPreferenceEntity.channel == channel,
        )
        return self.session.execute(stmt).scalars().first()
