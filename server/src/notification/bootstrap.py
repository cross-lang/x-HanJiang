#!/usr/bin/env python3
"""通知子系统启动入口。

封装通知子系统的完整初始化流程：
1. 注册已配置的渠道 Provider
2. 启动失败重试 Worker（依赖 Redis）
main.py 只需调用 setup_notification_system() 一行。

同时承载通知重试 Handler：
从 Redis 重试队列取出失败通知，重新调用 Provider 发送，
由 scheduling.RetryWorker 驱动。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.config import settings
from src.core.logger import logger
from src.infras.notification import NotificationMessage, get_registry

NOTIFICATION_RETRY_QUEUE_KEY = "notification:retry_queue"


def handle_notification_retry(data: dict[str, Any]) -> bool:
    """处理单条通知重试任务。

    发送成功回写投递明细（status=success, receive_at）；
    发送失败回写重试次数与错误信息，并返回 False 保留待下次重试。

    Args:
        data: 从 Redis 队列取出的任务数据，含 delivery_id、channel、recipient、
            subject、content、retry_count

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
    delivery_id = data.get("delivery_id")
    if delivery_id is not None:
        _sync_delivery_state(delivery_id=delivery_id, success=success)
    if success:
        logger.info(
            "Notification retry success: delivery_id={} channel={} recipient={}",
            delivery_id,
            channel,
            data["recipient"],
        )
    return success


def _sync_delivery_state(delivery_id: int, success: bool) -> None:
    """重试后回写投递明细状态（失败不影响主流程）。

    Args:
        delivery_id: 投递明细 ID
        success: 本次重试是否成功
    """
    try:
        from src.infras.database import get_cached_database_provider
        from src.repositories.notification_delivery_repository import NotificationDeliveryRepository

        session = get_cached_database_provider().get_session_factory()()
        try:
            repo = NotificationDeliveryRepository(session=session)
            delivery = repo.get_by_id(delivery_id)
            if delivery is None:
                logger.warning("Retry delivery not found: id={}", delivery_id)
                return
            if success:
                repo.mark_sent(delivery)
            else:
                repo.mark_retry_failed(delivery, error_message="Retry attempt failed")
            repo.commit()
        finally:
            session.close()
    except Exception as exc:
        logger.error("Failed to sync delivery state after retry: id={} error={}", delivery_id, exc)


def setup_notification_system() -> asyncio.Task[Any] | None:
    """初始化通知子系统，返回重试 Worker 的 Task（未启动则返回 None）。"""
    if not settings.notification.enabled:
        logger.info("Notification system disabled, skipping")
        return None
    # 1. 从数据库注册渠道 Provider（优先 DB，未配置的渠道回退 .env）
    from src.infras.notification import reload_providers_from_db

    reload_providers_from_db()
    # 2. 启动失败重试 Worker
    from src.scheduling.retry_worker import RetryWorker

    worker = RetryWorker(
        queue_key=NOTIFICATION_RETRY_QUEUE_KEY,
        handler=handle_notification_retry,
        interval_seconds=settings.notification.retry_interval_seconds,
    )
    task = worker.start()
    logger.info("Notification retry worker scheduled")
    return task
