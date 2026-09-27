#!/usr/bin/env python3
"""通知重试 Handler。

从 Redis 重试队列取出失败通知，重新调用 Provider 发送。
由 scheduling.RetryWorker 驱动。
"""

from __future__ import annotations

from typing import Any

from src.core.logger import logger
from src.infras.notification import NotificationMessage, get_registry

NOTIFICATION_RETRY_QUEUE_KEY = "notification:retry_queue"


def handle_notification_retry(data: dict[str, Any]) -> bool:
    """处理单条通知重试任务。

    Args:
        data: 从 Redis 队列取出的任务数据，包含 channel、recipient、subject、content 等

    Returns:
        True=发送成功（出队），False=发送失败（保留待下次重试）
    """
    registry = get_registry()
    channel = data["channel"]

    provider = registry.get(channel)
    if provider is None:
        logger.warning("No provider for channel={}, dropping retry task", channel)
        return True  # 没有 provider，直接丢弃

    message = NotificationMessage(
        recipient=data["recipient"],
        subject=data.get("subject", ""),
        content=data.get("content", ""),
    )

    success = provider.send(message)
    if success:
        logger.info(
            "Notification retry success: channel={} recipient={}",
            channel,
            data["recipient"],
        )
    return success
