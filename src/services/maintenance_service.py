"""系统维护通知服务。

管理员触发维护通知，广播给全体活跃用户。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import NotificationEvent
from src.core.logger import logger
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.user_repository import UserRepository


class MaintenanceService:
    """系统维护通知服务。

    通过 NotificationDispatcher 向全体活跃用户发送
    system.maintenance 事件通知。
    """

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        session: Session,
    ) -> None:
        self._dispatcher = dispatcher
        self._session = session

    def notify_all(
        self,
        maintenance_time: str,
        duration: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """广播维护通知给全体活跃用户。

        Args:
            maintenance_time: 维护开始时间
            duration: 预计持续时长
            reason: 维护原因（可选）
            metadata: 扩展元数据

        Returns:
            成功发送的用户数
        """
        repo = UserRepository(session=self._session)
        users, _ = repo.search(status="active", skip=0, limit=10000)

        variables: dict[str, Any] = {
            "maintenance_time": maintenance_time,
            "duration": duration,
        }
        if reason:
            variables["reason"] = reason

        sent_count = 0
        for user in users:
            try:
                self._dispatcher.dispatch_for_user(
                    user_id=user.id,
                    event_type=NotificationEvent.SYSTEM_MAINTENANCE,
                    variables=variables,
                    metadata=metadata,
                )
                sent_count += 1
            except Exception as e:
                logger.warning(
                    f"Maintenance notification failed for user={user.id}: {e}"
                )

        logger.info(
            "Maintenance notification completed: time=%s users=%d/%d",
            maintenance_time, sent_count, len(users),
        )
        return sent_count
