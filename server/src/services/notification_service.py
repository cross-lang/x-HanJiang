"""通知业务逻辑层。

作为 API 层与通知子系统之间的门面（Facade），
封装通知发送、查询、统计等业务操作。

调用链路：API → NotificationService → NotificationDispatcher → Provider
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.models.entities.notification_entity import NotificationRecordEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.notification_repository import NotificationRepository
from src.schemas.common import PaginatedResponse
from src.schemas.notification import NotificationRecordResponse


class NotificationService:
    """通知业务逻辑层。

    内部委托 NotificationDispatcher 完成实际调度。
    """

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        session: Session,
    ) -> None:
        self._dispatcher = dispatcher
        self._session = session
        self._repository = NotificationRepository(session=session)

    # ── 发送 ───────────────────────────────────────────────

    def send_for_user(
        self,
        user_id: int,
        event_type: str,
        variables: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[NotificationRecordEntity]:
        """根据用户通知配置自动发送通知。"""
        return self._dispatcher.dispatch_for_user(
            user_id=user_id,
            event_type=event_type,
            variables=variables,
            metadata=metadata,
        )

    def send_manual(
        self,
        event_type: str,
        recipients: dict[str, str],
        variables: dict[str, Any] | None = None,
        channels: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[NotificationRecordEntity]:
        """手动指定接收人发送通知（调试用）。"""
        return self._dispatcher.dispatch(
            event_type=event_type,
            recipients=recipients,
            variables=variables,
            channels=channels,
            metadata=metadata,
        )

    # ── 查询 ───────────────────────────────────────────────

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        channel: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[NotificationRecordResponse]:
        """分页查询通知记录。"""
        query = self._session.query(NotificationRecordEntity)

        if event_type:
            query = query.filter(NotificationRecordEntity.event_type == event_type)
        if channel:
            query = query.filter(NotificationRecordEntity.channel == channel)
        if status:
            query = query.filter(NotificationRecordEntity.status == status)

        total = query.count()
        items = (
            query.order_by(NotificationRecordEntity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return PaginatedResponse[NotificationRecordResponse](
            items=[NotificationRecordResponse.model_validate(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    def get_record(self, notification_id: int) -> NotificationRecordResponse:
        """查询单条通知记录，不存在则抛 NotFoundException。"""
        from src.core.exceptions import NotFoundException

        record = self._repository.get_by_id(notification_id)
        if record is None:
            raise NotFoundException(message="通知记录不存在")
        return NotificationRecordResponse.model_validate(record)

    # ── 统计 ───────────────────────────────────────────────

    def get_stats(self) -> dict[str, int]:
        """查询通知发送统计。"""
        return {
            "total": self._repository.count(),
            "success": self._repository.count_by_status("success"),
            "failed": self._repository.count_by_status("failed"),
            "pending": self._repository.count_by_status("pending"),
        }