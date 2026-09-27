"""通知记录数据访问层。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.entities.notification_entity import NotificationRecordEntity
from src.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[NotificationRecordEntity, int]):
    """通知记录 Repository。"""

    model_class = NotificationRecordEntity

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def get_by_event_type(
        self, event_type: str, skip: int = 0, limit: int = 100
    ) -> list[NotificationRecordEntity]:
        """按事件类型查询通知记录。"""
        stmt = (
            self._base_query()
            .where(self.model_class.event_type == event_type)
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_pending_retry(self, limit: int = 50) -> list[NotificationRecordEntity]:
        """查询待重试的失败记录。"""
        stmt = (
            self._base_query()
            .where(
                self.model_class.status == "failed",
                self.model_class.retry_count < self.model_class.max_retries,
            )
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_by_status(self, status: str) -> int:
        """按状态统计通知数量。"""
        from sqlalchemy import func

        stmt = select(func.count()).where(self.model_class.status == status)
        return self.session.execute(stmt).scalar() or 0

    def search_records(
        self,
        event_type: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[NotificationRecordEntity], int]:
        """按事件类型/渠道/状态分页查询通知记录（按时间倒序）。"""
        from sqlalchemy import func

        conditions = []
        if event_type:
            conditions.append(self.model_class.event_type == event_type)
        if channel:
            conditions.append(self.model_class.channel == channel)
        if status:
            conditions.append(self.model_class.status == status)

        total = (
            self.session.execute(
                select(func.count())
                .select_from(
                    select(self.model_class).where(*conditions).subquery()
                )
            ).scalar()
            or 0
        )
        rows = list(
            self.session.execute(
                select(self.model_class)
                .where(*conditions)
                .order_by(self.model_class.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    @staticmethod
    def _entity_name() -> str:
        return "通知记录"
