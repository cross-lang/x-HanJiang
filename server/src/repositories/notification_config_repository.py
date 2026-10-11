"""用户通知渠道配置数据访问层。"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models.entities.notification_config_entity import UserNotificationConfigEntity
from src.models.entities.user_event_notification_entity import UserEventNotificationEntity
from src.repositories.base_repository import BaseRepository


class UserNotificationConfigRepository(BaseRepository[UserNotificationConfigEntity, int]):
    """用户通知渠道配置 Repository。

    渠道级配置（user_notification_configs，一行 = 用户 × 渠道）与
    事件订阅关系（user_event_notifications，一行 = 渠道配置 × 事件）分表维护，
    本类同时提供两表的访问方法。
    """

    model_class = UserNotificationConfigEntity

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    # ── 渠道配置查询 ────────────────────────────────────────

    def list_by_user_id(self, user_id: int) -> list[UserNotificationConfigEntity]:
        """查询用户全部渠道配置（含未启用，供管理界面展示）。"""
        stmt = self._base_query().where(self.model_class.user_id == user_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_user_channel(self, user_id: int, channel: str) -> UserNotificationConfigEntity | None:
        """按 (user, channel) 唯一键查询渠道配置。"""
        stmt = self._base_query().where(
            self.model_class.user_id == user_id,
            self.model_class.channel == channel,
        )
        return self.session.execute(stmt).scalars().first()

    def get_or_create_channel_config(self, user_id: int, channel: str) -> UserNotificationConfigEntity:
        """按 (user, channel) 取渠道配置，不存在则创建默认行（recipient 空、启用）。

        事务提交由服务层控制，此处仅 flush。

        Args:
            user_id: 用户 ID
            channel: 渠道标识
        """
        config = self.get_by_user_channel(user_id, channel)
        if config is None:
            config = self.create(
                UserNotificationConfigEntity(user_id=user_id, channel=channel, recipient="", enabled=True)
            )
        return config

    # ── 事件订阅（user_event_notifications）─────────────────

    def list_subscriptions(self, user_id: int) -> list[UserEventNotificationEntity]:
        """查询用户全部事件订阅行（join 渠道配置过滤 user_id）。"""
        stmt = (
            select(UserEventNotificationEntity)
            .join(
                self.model_class,
                self.model_class.id == UserEventNotificationEntity.config_id,
            )
            .where(self.model_class.user_id == user_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_subscription(self, config_id: int, event_type: str) -> UserEventNotificationEntity | None:
        """按 (config, event) 唯一键查询订阅行。"""
        stmt = select(UserEventNotificationEntity).where(
            UserEventNotificationEntity.config_id == config_id,
            UserEventNotificationEntity.event_type == event_type,
        )
        return self.session.execute(stmt).scalars().first()

    def subscribe(self, config_id: int, event_type: str) -> None:
        """订阅：把渠道配置与事件建立映射（幂等，已存在则跳过）。"""
        if self.get_subscription(config_id, event_type) is None:
            self.session.add(UserEventNotificationEntity(config_id=config_id, event_type=event_type))
            self.session.flush()

    def unsubscribe(self, config_id: int, event_type: str) -> None:
        """退订：删除渠道配置与事件的映射行（幂等，不存在则跳过）。"""
        self.session.execute(
            delete(UserEventNotificationEntity).where(
                UserEventNotificationEntity.config_id == config_id,
                UserEventNotificationEntity.event_type == event_type,
            )
        )

    # ── 调度读取 ────────────────────────────────────────────

    def build_recipients_map(self, user_id: int, event_type: str) -> dict[str, str]:
        """构建事件下 渠道→接收方 映射（仅 已订阅 + 渠道启用 行，station 渠道不返回）。

        Args:
            user_id: 用户 ID
            event_type: 事件类型

        Returns:
            {"email": "a@b.com", "dingtalk": "https://oapi.dingtalk.com/...", ...}
        """
        stmt = (
            select(self.model_class)
            .join(
                UserEventNotificationEntity,
                UserEventNotificationEntity.config_id == self.model_class.id,
            )
            .where(
                self.model_class.user_id == user_id,
                UserEventNotificationEntity.event_type == event_type,
                self.model_class.enabled.is_(True),
            )
        )
        rows = list(self.session.execute(stmt).scalars().all())
        result: dict[str, str] = {}
        for row in rows:
            if row.channel == "station":
                # 站内信不通过 dispatcher 外发，由 station_service 直接写站内信表
                continue
            if row.recipient:
                result[row.channel] = row.recipient
        return result

    @staticmethod
    def _entity_name() -> str:
        return "用户通知配置"
