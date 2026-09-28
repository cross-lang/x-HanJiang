#!/usr/bin/env python3
"""
站内信数据访问实现
本模块提供站内信（channel=station 的通知记录）Repository 的 SQLAlchemy 实现。
支持未读数统计、分页查询、标记已读、全部已读。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    StationMessageRepository: 站内信数据访问 SQLAlchemy 实现
"""

from sqlalchemy import func, select, update

from src.constants.enums import NotificationChannel, StationMessageStatus
from src.models.entities.notification_entity import NotificationRecordEntity
from src.repositories.base_repository import BaseRepository


class StationMessageRepository(BaseRepository[NotificationRecordEntity, int]):
    """站内信数据访问 SQLAlchemy 实现。"""

    model_class = NotificationRecordEntity

    def _station_query(self, user_id: int):
        """站内信基础查询（按收件人过滤）。"""
        return select(NotificationRecordEntity).where(
            NotificationRecordEntity.channel == NotificationChannel.STATION.value,
            NotificationRecordEntity.recipient == f"user:{user_id}",
        )

    def unread_count(self, user_id: int) -> int:
        """统计用户未读站内信数量。"""
        stmt = self._station_query(user_id).where(NotificationRecordEntity.status == StationMessageStatus.UNREAD.value)
        return self.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0

    def list_messages(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[NotificationRecordEntity], int]:
        """分页查询用户站内信（按时间倒序）。"""
        total = (
            self.session.execute(select(func.count()).select_from(self._station_query(user_id).subquery())).scalar()
            or 0
        )
        rows = list(
            self.session.execute(
                self._station_query(user_id)
                .order_by(NotificationRecordEntity.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    def get_message(self, user_id: int, msg_id: int) -> NotificationRecordEntity | None:
        """查询用户某条站内信。"""
        return (
            self.session.execute(self._station_query(user_id).where(NotificationRecordEntity.id == msg_id))
            .scalars()
            .first()
        )

    def mark_read(self, msg: NotificationRecordEntity) -> None:
        """标记单条已读（实体已由调用方持有，此处仅落状态）。"""
        msg.status = StationMessageStatus.READ.value
        self.session.flush()

    def mark_all_read(self, user_id: int) -> None:
        """将用户全部未读站内信标记为已读。"""
        self.session.execute(
            update(NotificationRecordEntity)
            .where(
                NotificationRecordEntity.channel == NotificationChannel.STATION.value,
                NotificationRecordEntity.recipient == f"user:{user_id}",
                NotificationRecordEntity.status == StationMessageStatus.UNREAD.value,
            )
            .values(status=StationMessageStatus.READ.value)
        )
        self.session.flush()
