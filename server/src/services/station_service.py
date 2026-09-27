#!/usr/bin/env python3
"""站内信服务。"""

from sqlalchemy import select, func

from src.infras.database import get_cached_database_provider
from src.models.entities.notification_entity import NotificationRecordEntity


class StationMessageService:
    """站内信服务。"""

    def __init__(self):
        self._session = get_cached_database_provider().get_session_factory()()

    def unread_count(self, user_id: int) -> int:
        return self._session.execute(
            select(func.count(NotificationRecordEntity.id))
            .where(
                NotificationRecordEntity.channel == "station",
                NotificationRecordEntity.recipient == f"user:{user_id}",
                NotificationRecordEntity.status == "unread",
            )
        ).scalar() or 0

    def list_messages(self, user_id: int, page: int, page_size: int) -> dict:
        base = select(NotificationRecordEntity).where(
            NotificationRecordEntity.channel == "station",
            NotificationRecordEntity.recipient == f"user:{user_id}",
        ).order_by(NotificationRecordEntity.created_at.desc())

        total = self._session.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
        rows = self._session.execute(base.offset((page - 1) * page_size).limit(page_size)).scalars().all()

        items = [
            {
                "id": r.id,
                "title": r.subject,
                "content": r.content,
                "is_read": r.status == "read",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]
        return {"total": total, "items": items}

    def mark_read(self, user_id: int, msg_id: int) -> None:
        msg = self._session.execute(
            select(NotificationRecordEntity).where(
                NotificationRecordEntity.id == msg_id,
                NotificationRecordEntity.recipient == f"user:{user_id}",
            )
        ).scalars().first()
        if msg:
            msg.status = "read"
            self._session.commit()

    def mark_all_read(self, user_id: int) -> None:
        self._session.query(NotificationRecordEntity).filter(
            NotificationRecordEntity.channel == "station",
            NotificationRecordEntity.recipient == f"user:{user_id}",
            NotificationRecordEntity.status == "unread",
        ).update({"status": "read"})
        self._session.commit()

    def send_station(self, user_id: int, title: str, content: str) -> None:
        """发送站内信给指定用户。"""
        msg = NotificationRecordEntity(
            event_type="station.message",
            channel="station",
            recipient=f"user:{user_id}",
            subject=title,
            content=content,
            status="unread",
            retry_count=0,
            max_retries=0,
        )
        self._session.add(msg)
        self._session.commit()
