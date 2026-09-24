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

from src.constants.enums import NotificationChannel, NotificationEvent
from src.core.logger import logger
from src.notification.dispatcher import NotificationDispatcher


class AlertService:
    """统一系统告警服务。

    通过 NotificationDispatcher 发送 system.alert 事件，
    自动走模板渲染和多渠道投递。
    """

    def __init__(self, dispatcher: NotificationDispatcher) -> None:
        self._dispatcher = dispatcher

    def send(
        self,
        subject: str,
        message: str,
        recipients: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """发送系统告警。

        Args:
            subject: 告警标题
            message: 告警内容
            recipients: 渠道→接收人映射，省略则使用默认路由
            metadata: 扩展元数据

        Returns:
            是否全部发送成功
        """
        variables = {
            "alert_title": subject,
            "alert_message": message,
        }

        try:
            if recipients:
                records = self._dispatcher.dispatch(
                    event_type=NotificationEvent.SYSTEM_ALERT,
                    recipients=recipients,
                    variables=variables,
                    metadata=metadata,
                )
            else:
                # 无 recipients 时无法自动发送（告警通常需要指定接收人）
                logger.warning("Alert send skipped: no recipients provided")
                return False

            return all(r.status == "success" for r in records)
        except Exception as exc:
            logger.error("Alert send failed: %s", exc)
            return False
