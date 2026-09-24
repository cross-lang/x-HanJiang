#!/usr/bin/env python3
"""系统告警服务。

委托 NotificationDispatcher 发送告警，复用通知系统的：
- 模板渲染
- 多渠道发送
- 发送记录
- 失败重试
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import NotificationEvent
from src.core.logger import logger
from src.models.entities.notification_entity import NotificationRecordEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.user_repository import UserRepository


class AlertService:
    """统一系统告警服务。

    支持两种发送模式：
    - send(): 指定接收人发送（供外部监控 Webhook 调用）
    - broadcast(): 广播给全体活跃用户（供健康检查等内部场景调用）
    """

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        session: Session | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._session = session

    def send(
        self,
        subject: str,
        message: str,
        recipients: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> list[NotificationRecordEntity]:
        """发送系统告警到指定接收人。

        Args:
            subject: 告警标题
            message: 告警内容
            recipients: 渠道→接收人映射，如 {"email": "a@b.com"}
            metadata: 扩展元数据

        Returns:
            通知记录列表
        """
        variables = {
            "alert_title": subject,
            "alert_message": message,
        }
        return self._dispatcher.dispatch(
            event_type=NotificationEvent.SYSTEM_ALERT,
            recipients=recipients,
            variables=variables,
            metadata=metadata,
        )

    def broadcast(
        self,
        subject: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """广播系统告警给全体活跃用户。

        Args:
            subject: 告警标题
            message: 告警内容
            metadata: 扩展元数据

        Returns:
            成功发送的用户数
        """
        if self._session is None:
            logger.warning("Alert broadcast skipped: no database session")
            return 0

        repo = UserRepository(session=self._session)
        users, _ = repo.search(status="active", skip=0, limit=10000)

        sent_count = 0
        for user in users:
            try:
                self._dispatcher.dispatch_for_user(
                    user_id=user.id,
                    event_type=NotificationEvent.SYSTEM_ALERT,
                    variables={
                        "alert_title": subject,
                        "alert_message": message,
                    },
                    metadata=metadata,
                )
                sent_count += 1
            except Exception as e:
                logger.warning(
                    f"Alert broadcast failed for user={user.id}: {e}"
                )

        logger.info(
            "Alert broadcast completed: subject=%s users=%d/%d",
            subject, sent_count, len(users),
        )
        return sent_count
