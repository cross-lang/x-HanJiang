"""用户通知渠道配置数据访问层。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.entities.notification_config_entity import (
    UserNotificationConfigEntity,
)
from src.repositories.base_repository import BaseRepository


class UserNotificationConfigRepository(
    BaseRepository[UserNotificationConfigEntity, int]
):
    """用户通知渠道配置 Repository。"""

    model_class = UserNotificationConfigEntity

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_enabled_by_user_id(
        self, user_id: int
    ) -> list[UserNotificationConfigEntity]:
        """查询用户所有已启用的通知渠道配置。"""
        stmt = (
            self._base_query()
            .where(
                self.model_class.user_id == user_id,
                self.model_class.enabled.is_(True),
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_user_and_channel(
        self, user_id: int, channel: str
    ) -> UserNotificationConfigEntity | None:
        """按用户ID和渠道查询配置。"""
        stmt = self._base_query().where(
            self.model_class.user_id == user_id,
            self.model_class.channel == channel,
        )
        return self.session.execute(stmt).scalars().first()

    def build_recipients_map(self, user_id: int) -> dict[str, str]:
        """构建渠道→接收人映射（仅已启用的渠道）。

        Returns:
            {"email": "a@b.com", "dingtalk": "zhangsan", ...}
        """
        configs = self.get_enabled_by_user_id(user_id)
        return {c.channel: c.recipient for c in configs}

    @staticmethod
    def _entity_name() -> str:
        return "用户通知配置"
