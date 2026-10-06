#!/usr/bin/env python3
"""通用重试 Worker。
从 Redis ZSET 消费到期的失败任务，调用用户提供的 handler 重新执行。
支持多个队列，每个队列对应一个 RetryWorker 实例。

Usage:
    from src.scheduling.retry_worker import RetryWorker
    async def my_handler(data: dict) -> bool:
        # 处理任务，返回 True=成功, False=失败
        return True
    worker = RetryWorker(
        queue_key="my:retry_queue",
        handler=my_handler,
        interval_seconds=60,
        max_retries=3,
    )
    task = worker.start()  # 返回 asyncio.Task
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from typing import Any

from src.core.logger import logger

# handler 签名：接收任务数据 dict，返回 True=成功(出队), False=失败(保留待下次)
RetryHandler = Callable[[dict[str, Any]], Any]


class RetryWorker:
    """通用 Redis ZSET 重试 Worker。
    从指定的 Redis ZSET 队列中取出到期任务，调用 handler 执行重试。
    任务数据为 JSON 字符串，score 为下次重试时间戳（Unix 时间戳）。

    Attributes:
        queue_key: Redis ZSET 的 key
        handler: 任务处理函数，接收 data dict，返回 bool（True=成功）
        interval_seconds: 轮询间隔（秒）
        max_retries: 最大重试次数，超过后丢弃
        batch_size: 每次轮询最多取多少条
    """

    def __init__(
        self,
        queue_key: str,
        handler: RetryHandler,
        interval_seconds: int = 60,
        max_retries: int = 3,
        batch_size: int = 10,
    ) -> None:
        self._queue_key = queue_key
        self._handler = handler
        self._interval = interval_seconds
        self._max_retries = max_retries
        self._batch_size = batch_size
        self._task: asyncio.Task[Any] | None = None

    def start(self) -> asyncio.Task[Any]:
        """启动后台 worker，返回 asyncio.Task。"""
        self._task = asyncio.create_task(self._run())
        logger.info(
            "RetryWorker started: queue={}, interval={}s, max_retries={}",
            self._queue_key,
            self._interval,
            self._max_retries,
        )
        return self._task

    def stop(self) -> None:
        """停止 worker。"""
        if self._task:
            self._task.cancel()
            logger.info("RetryWorker stopped: queue={}", self._queue_key)

    async def _run(self) -> None:
        """主循环：轮询队列 → 取到期任务 → 调 handler → 成功出队/失败保留。"""
        while True:
            try:
                await self._process_batch()
            except asyncio.CancelledError:
                logger.info("RetryWorker cancelled: queue={}", self._queue_key)
                raise
            except Exception as exc:
                logger.error("RetryWorker error: queue={}, error={}", self._queue_key, exc)
            await asyncio.sleep(self._interval)

    async def _process_batch(self) -> None:
        """处理一批到期任务。"""
        from src.infras.cache import get_cached_cache_provider

        redis = get_cached_cache_provider()
        now = time.time()
        items = redis.zrangebyscore(self._queue_key, 0, now, start=0, num=self._batch_size)
        for raw in items:
            data: dict[str, Any] = json.loads(raw)
            retry_count = data.get("retry_count", 1)
            try:
                success = self._handler(data)
                if success:
                    redis.zrem(self._queue_key, raw)
                    logger.info(
                        "Retry success: queue={}, retry_count={}",
                        self._queue_key,
                        retry_count,
                    )
                elif retry_count >= self._max_retries:
                    redis.zrem(self._queue_key, raw)
                    logger.warning(
                        "Retry exhausted: queue={}, retry_count={}",
                        self._queue_key,
                        retry_count,
                    )
            except Exception as exc:
                logger.error(
                    "Retry attempt failed: queue={}, error={}",
                    self._queue_key,
                    exc,
                )
