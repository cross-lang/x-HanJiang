"""通知业务逻辑层。
作为 API 层与通知子系统之间的门面（Facade），
封装通知发送、查询、统计等业务操作。
调用链路：API → NotificationService → NotificationDispatcher → Provider
"""

from __future__ import annotations

from typing import Any

from src.constants.enums import NotificationStatus
from src.models.entities.notification_entity import NotificationRecordEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.notification_repository import NotificationRepository
from src.schemas.admin.notification import NotificationRecordResponse
from src.schemas.common import PaginatedResponse


class NotificationService:
    """通知业务逻辑层。
    内部委托 NotificationDispatcher 完成实际调度。
    数据查询仅通过 NotificationRepository，不直接操作数据库会话。
    """

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        repository: NotificationRepository,
    ) -> None:
        self._dispatcher = dispatcher
        self._repository = repository

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

    # ── 查询 ───────────────────────────────────────────────

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        channel: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[NotificationRecordResponse]:
        """分页查询通知记录（经仓库）。"""
        skip = (page - 1) * page_size
        items, total = self._repository.search_records(
            event_type=event_type,
            channel=channel,
            status=status,
            skip=skip,
            limit=page_size,
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
            "success": self._repository.count_by_status(NotificationStatus.SUCCESS.value),
            "failed": self._repository.count_by_status(NotificationStatus.FAILED.value),
            "pending": self._repository.count_by_status("pending"),
        }
