"""通知重试 Worker。

从 Redis ZSET 重试队列消费失败通知，按指数退避间隔重试。

启动方式：在 lifespan 中作为后台 asyncio.Task 运行。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from src.core.logger import logger
from src.infras.notification import NotificationMessage, get_registry

_RETRY_QUEUE_KEY = "notification:retry_queue"


async def run_retry_worker(interval_seconds: int = 60) -> None:
    """后台重试 Worker 主循环。

    Args:
        interval_seconds: 轮询间隔（秒）
    """
    logger.info("Notification retry worker started, interval=%ds", interval_seconds)
    registry = get_registry()

    while True:
        try:
            now = time.time()

            try:
                from src.infras.cache import get_cached_cache_provider

                redis = get_cached_cache_provider()
            except Exception:
                await asyncio.sleep(interval_seconds)
                continue

            # 取出到期的重试项
            items = redis.zrangebyscore(_RETRY_QUEUE_KEY, 0, now, start=0, num=10)
            for raw in items:
                data: dict[str, Any] = json.loads(raw)
                channel = data["channel"]

                provider = registry.get(channel)
                if provider is None:
                    redis.zrem(_RETRY_QUEUE_KEY, raw)
                    continue

                message = NotificationMessage(
                    recipient=data["recipient"],
                    subject=data.get("subject", ""),
                    content=data.get("content", ""),
                )

                try:
                    success = provider.send(message)
                    if success:
                        redis.zrem(_RETRY_QUEUE_KEY, raw)
                        logger.info(
                            "Notification retry success: channel=%s recipient=%s",
                            channel,
                            data["recipient"],
                        )
                    elif data.get("retry_count", 0) >= 3:
                        redis.zrem(_RETRY_QUEUE_KEY, raw)
                        logger.warning(
                            "Notification retry exhausted: channel=%s recipient=%s",
                            channel,
                            data["recipient"],
                        )
                except Exception as exc:
                    logger.error("Notification retry attempt failed: %s", exc)

        except asyncio.CancelledError:
            logger.info("Notification retry worker cancelled")
            raise
        except Exception as exc:
            logger.error("Notification retry worker error: %s", exc)

        await asyncio.sleep(interval_seconds)
