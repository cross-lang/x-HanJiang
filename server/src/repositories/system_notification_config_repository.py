#!/usr/bin/env python3
"""
系统通知配置数据访问实现

本模块提供系统级通知渠道配置（system_notification_configs）Repository 的 SQLAlchemy 实现。
支持渠道配置查询与按渠道 upsert。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    SystemNotificationConfigRepository: 系统通知配置数据访问 SQLAlchemy 实现
"""

from sqlalchemy import select

from src.models.entities.system_notification_config_entity import (
    SystemNotificationConfigEntity,
)
from src.repositories.base_repository import BaseRepository


class SystemNotificationConfigRepository(
    BaseRepository[SystemNotificationConfigEntity, int]
):
    """系统通知配置数据访问 SQLAlchemy 实现。"""

    model_class = SystemNotificationConfigEntity

    def get_by_channel(self, channel: str) -> SystemNotificationConfigEntity | None:
        """按渠道查询配置。"""
        stmt = select(SystemNotificationConfigEntity).where(
            SystemNotificationConfigEntity.channel == channel
        )
        return self.session.execute(stmt).scalars().first()

    def list_all(self) -> list[SystemNotificationConfigEntity]:
        """查询全部渠道配置。"""
        stmt = select(SystemNotificationConfigEntity).order_by(
            SystemNotificationConfigEntity.channel.asc()
        )
        return list(self.session.execute(stmt).scalars().all())

    def upsert(
        self,
        channel: str,
        config_json: str,
        enabled: bool,
    ) -> SystemNotificationConfigEntity:
        """按渠道更新或创建配置。"""
        row = self.get_by_channel(channel)
        if row:
            row.config_json = config_json
            row.enabled = enabled
        else:
            row = SystemNotificationConfigEntity(
                channel=channel,
                config_json=config_json,
                enabled=enabled,
            )
            self.session.add(row)
        self.session.flush()
        return row
