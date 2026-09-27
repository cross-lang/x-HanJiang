#!/usr/bin/env python3
"""站内信服务。

仅调用 StationMessageRepository 存取数据，不直接操作数据库会话。
"""

from src.models.entities.notification_entity import NotificationRecordEntity
from src.repositories.station_message_repository import StationMessageRepository


class StationMessageService:
    """站内信服务。"""

    def __init__(self, repository: StationMessageRepository) -> None:
        self._repository = repository

    def unread_count(self, user_id: int) -> int:
        return self._repository.unread_count(user_id)

    def list_messages(self, user_id: int, page: int, page_size: int) -> dict:
        skip = (page - 1) * page_size
        rows, total = self._repository.list_messages(
            user_id=user_id, skip=skip, limit=page_size
        )
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
        msg = self._repository.get_message(user_id, msg_id)
        if msg:
            self._repository.mark_read(msg)
            self._repository.commit()

    def mark_all_read(self, user_id: int) -> None:
        self._repository.mark_all_read(user_id)
        self._repository.commit()

    def send_station(self, user_id: int, title: str, content: str) -> None:
        """发送站内信给指定用户（经仓库）。"""
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
        self._repository.create(msg)
        self._repository.commit()
