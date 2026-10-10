"""用户通知渠道配置数据访问层。"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from src.models.entities.notification_config_entity import UserNotificationConfigEntity
from src.repositories.base_repository import BaseRepository


class UserNotificationConfigRepository(BaseRepository[UserNotificationConfigEntity, int]):
    """用户通知渠道配置 Repository。

    表结构已合并原 user_notification_preferences：一行 = (user, event_type, channel)。
    """

    model_class = UserNotificationConfigEntity

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    # ── 查询 ────────────────────────────────────────────────

    def list_by_user_id(self, user_id: int) -> list[UserNotificationConfigEntity]:
        """查询用户全部通知配置（含未启用，供管理界面展示）。"""
        stmt = self._base_query().where(self.model_class.user_id == user_id)
        return list(self.session.execute(stmt).scalars().all())

    def list_by_user_and_event(self, user_id: int, event_type: str) -> list[UserNotificationConfigEntity]:
        """查询用户在指定事件下的所有渠道配置。"""
        stmt = self._base_query().where(
            self.model_class.user_id == user_id,
            self.model_class.event_type == event_type,
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_user_event_channel(
        self, user_id: int, event_type: str, channel: str
    ) -> UserNotificationConfigEntity | None:
        """按 (user, event, channel) 唯一键查询。"""
        stmt = self._base_query().where(
            self.model_class.user_id == user_id,
            self.model_class.event_type == event_type,
            self.model_class.channel == channel,
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_user_and_channel(self, user_id: int, channel: str) -> list[UserNotificationConfigEntity]:
        """查询用户在指定渠道下所有事件的配置（用于 recipient 同步）。"""
        stmt = self._base_query().where(
            self.model_class.user_id == user_id,
            self.model_class.channel == channel,
        )
        return list(self.session.execute(stmt).scalars().all())

    # ── 写入 ────────────────────────────────────────────────

    def upsert_channel_recipient(
        self,
        user_id: int,
        channel: str,
        recipient: str,
        enabled: bool = True,
    ) -> int:
        """同步刷新用户在某渠道下所有事件行的 recipient。

        渠道级 recipient（邮箱地址 / webhook URL）与事件无关，
        这里把该用户在该 channel 下已有的所有 event 行的 recipient 统一更新；
        若该用户在该 channel 下还没有任何行，则跳过（事件×渠道开关由 update_notification_preferences 维护）。

        Args:
            user_id: 用户 ID
            channel: 渠道标识
            recipient: 接收方单值
            enabled: 是否同时启用该渠道

        Returns:
            int: 受影响行数
        """
        result = self.session.execute(
            update(self.model_class)
            .where(
                self.model_class.user_id == user_id,
                self.model_class.channel == channel,
            )
            .values(recipient=recipient, enabled=enabled)
        )
        return int(cast(CursorResult[Any], result).rowcount or 0)

    def build_recipients_map(self, user_id: int, event_type: str) -> dict[str, str]:
        """构建事件下 渠道→接收方 映射（仅 enabled 行，station 渠道不返回）。

        Args:
            user_id: 用户 ID
            event_type: 事件类型

        Returns:
            {"email": "a@b.com", "dingtalk": "https://oapi.dingtalk.com/...", ...}
        """
        rows = self.list_by_user_and_event(user_id, event_type)
        result: dict[str, str] = {}
        for row in rows:
            if not row.enabled:
                continue
            if row.channel == "station":
                # 站内信不通过 dispatcher 外发，由 station_service 直接写站内信表
                continue
            if row.recipient:
                result[row.channel] = row.recipient
        return result

    @staticmethod
    def _entity_name() -> str:
        return "用户通知配置"

    # ── 类型占位（与原签名兼容，无运行时作用） ─────────────────
    def parse_recipient_items(self, raw: Any) -> list[dict[str, Any]]:  # pragma: no cover
        """已废弃：recipient 改为单值字符串，此方法仅为兼容旧引用保留。"""
        raise NotImplementedError("recipient 已改为单值字符串，不再支持 JSON 数组解析")
