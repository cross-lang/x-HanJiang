#!/usr/bin/env python3
"""站内信服务。
仅调用 StationMessageRepository 存取数据，不直接操作数据库会话。
"""

from src.constants.enums import NotificationChannel, NotificationEvent, StationMessageStatus
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
        rows, total = self._repository.list_messages(user_id=user_id, skip=skip, limit=page_size)
        items = [
            {
                "id": r.id,
                "title": r.subject,
                "content": r.content,
                "is_read": r.status == StationMessageStatus.READ.value,
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
        """发送站内信给指定用户（经仓库）。

        Args:
            user_id: 目标用户 ID
            title: 站内信标题
            content: 站内信正文
        """
        msg = NotificationRecordEntity(
            event_type=NotificationEvent.STATION_MESSAGE.mark,
            channel=NotificationChannel.STATION.value,
            recipient=f"user:{user_id}",
            subject=title,
            content=content,
            status=StationMessageStatus.UNREAD.value,
            retry_count=0,
            max_retries=0,
        )
        self._repository.create(msg)
        self._repository.commit()

    def send_station_batch(self, user_ids: list[int], title: str, content: str, event_type: str) -> None:
        """批量发送站内信给多个用户（单事务一次提交，供系统通知广播使用）。

        Args:
            user_ids: 目标用户 ID 列表
            title: 站内信标题
            content: 站内信正文
            event_type: 站内信事件类型（如 system.notice）
        """
        for user_id in user_ids:
            self._repository.create(
                NotificationRecordEntity(
                    event_type=event_type,
                    channel=NotificationChannel.STATION.value,
                    recipient=f"user:{user_id}",
                    subject=title,
                    content=content,
                    status=StationMessageStatus.UNREAD.value,
                    retry_count=0,
                    max_retries=0,
                )
            )
        self._repository.commit()
