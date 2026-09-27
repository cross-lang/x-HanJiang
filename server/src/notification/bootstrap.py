#!/usr/bin/env python3
"""通知子系统启动入口。

封装通知子系统的完整初始化流程：
1. 注册已配置的渠道 Provider
2. 启动失败重试 Worker（依赖 Redis）

main.py 只需调用 setup_notification_system() 一行。
"""

from __future__ import annotations

import asyncio

from src.core.config import settings
from src.core.logger import logger


def setup_notification_system() -> asyncio.Task | None:
    """初始化通知子系统，返回重试 Worker 的 Task（未启动则返回 None）。"""
    if not settings.notification.enabled:
        logger.info("Notification system disabled, skipping")
        return None

    # 1. 注册已配置的渠道 Provider
    from src.infras.notification import register_default_providers
    register_default_providers()

    # 2. 启动失败重试 Worker
    from src.notification.retry import NOTIFICATION_RETRY_QUEUE_KEY, handle_notification_retry
    from src.scheduling.retry_worker import RetryWorker

    worker = RetryWorker(
        queue_key=NOTIFICATION_RETRY_QUEUE_KEY,
        handler=handle_notification_retry,
        interval_seconds=settings.notification.retry_interval_seconds,
    )
    task = worker.start()
    logger.info("Notification retry worker scheduled")
    return task
