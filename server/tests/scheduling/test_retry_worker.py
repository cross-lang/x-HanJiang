#!/usr/bin/env python3
"""
通用重试 Worker 测试（src/scheduling/retry_worker.py）

Worker 从 Redis ZSET 消费到期任务并调用 handler 重试。本测试用 Fake ZSET
内存替身（patch src.infras.cache.get_cached_cache_provider），不连接真实 Redis，覆盖：
    - handler 成功 → 出队
    - handler 失败且未超最大重试次数 → 保留待下次
    - handler 失败但已超最大重试次数 → 丢弃
    - handler 抛异常 → 保留且不中断 worker
    - 主循环的 CancelledError 透传 / 普通异常捕获后继续
    - start / stop 生命周期
"""

import asyncio
import json

import pytest
import src.infras.cache as cache_module
from src.scheduling.retry_worker import RetryWorker


class FakeZsetRedis:
    """内存版 ZSET 替身：模拟"全部到期"，记录 zrem 行为。"""

    def __init__(self, items: list[str]) -> None:
        self.items = list(items)
        self.removed: list[str] = []

    def zrangebyscore(self, _key, _lo, _hi, start=0, num=0) -> list[str]:
        # 测试中只放到期任务，直接返回全部（忽略分页参数）
        return list(self.items)

    def zrem(self, _key, *members: str) -> int:
        for m in members:
            if m in self.items:
                self.items.remove(m)
            self.removed.append(m)
        return len(members)


def _task(raw: str, retry_count: int = 1) -> str:
    """构造一个可入队的任务 JSON 字符串。"""
    data = json.loads(raw)
    data["retry_count"] = retry_count
    return json.dumps(data, ensure_ascii=False)


def _make_worker(handler, *, max_retries: int = 3, interval: int = 0) -> RetryWorker:
    return RetryWorker(
        queue_key="test:retry",
        handler=handler,
        interval_seconds=interval,
        max_retries=max_retries,
        batch_size=10,
    )


def _patch_cache(monkeypatch, redis: FakeZsetRedis) -> None:
    monkeypatch.setattr(cache_module, "get_cached_cache_provider", lambda: redis)


class TestProcessBatch:
    """单批任务处理逻辑。"""

    async def test_success_removes_task(self, monkeypatch) -> None:
        """handler 返回 True → 任务出队。"""
        raw = _task('{"id": 1}')
        redis = FakeZsetRedis([raw])
        _patch_cache(monkeypatch, redis)
        worker = _make_worker(handler=lambda data: True)

        await worker._process_batch()

        assert redis.items == []
        assert redis.removed == [raw]

    async def test_failure_below_max_retries_keeps_task(self, monkeypatch) -> None:
        """handler 返回 False 且未超最大重试次数 → 保留，待下次轮询。"""
        raw = _task('{"id": 2}', retry_count=1)
        redis = FakeZsetRedis([raw])
        _patch_cache(monkeypatch, redis)
        worker = _make_worker(handler=lambda data: False, max_retries=3)

        await worker._process_batch()

        assert redis.items == [raw]
        assert redis.removed == []

    async def test_failure_exhausted_drops_task(self, monkeypatch) -> None:
        """handler 返回 False 且已达最大重试次数 → 丢弃。"""
        raw = _task('{"id": 3}', retry_count=3)
        redis = FakeZsetRedis([raw])
        _patch_cache(monkeypatch, redis)
        worker = _make_worker(handler=lambda data: False, max_retries=3)

        await worker._process_batch()

        assert redis.items == []
        assert redis.removed == [raw]

    async def test_handler_exception_keeps_task_and_survives(self, monkeypatch) -> None:
        """handler 抛异常 → 任务保留，异常不外抛（worker 不崩）。"""
        raw = _task('{"id": 4}', retry_count=1)
        redis = FakeZsetRedis([raw])
        _patch_cache(monkeypatch, redis)

        def boom(data: dict) -> bool:
            raise RuntimeError("处理失败")

        worker = _make_worker(handler=boom)
        await worker._process_batch()  # 不应抛异常

        assert redis.items == [raw]
        assert redis.removed == []

    async def test_empty_queue_noop(self, monkeypatch) -> None:
        """空队列直接返回，无副作用。"""
        redis = FakeZsetRedis([])
        _patch_cache(monkeypatch, redis)
        worker = _make_worker(handler=lambda data: True)

        await worker._process_batch()

        assert redis.items == []
        assert redis.removed == []


class TestRunLoop:
    """主循环异常分支。"""

    async def test_cancelled_error_propagates(self, monkeypatch) -> None:
        """主循环收到 CancelledError → 记录日志后继续向上抛出（便于 asyncio 取消）。"""

        async def _cancel_batch() -> None:
            raise asyncio.CancelledError()

        worker = _make_worker(handler=lambda data: True)
        monkeypatch.setattr(worker, "_process_batch", _cancel_batch)

        with pytest.raises(asyncio.CancelledError):
            await worker._run()

    async def test_generic_exception_is_logged_then_sleeps(self, monkeypatch) -> None:
        """普通异常被捕获并记录；第一轮抛异常、第二轮抛 CancelledError 以退出无限循环。"""
        state = {"calls": 0}

        async def _flaky_batch() -> None:
            state["calls"] += 1
            if state["calls"] == 1:
                raise ValueError("批次失败")
            raise asyncio.CancelledError()

        worker = _make_worker(handler=lambda data: True, interval=0)
        monkeypatch.setattr(worker, "_process_batch", _flaky_batch)

        with pytest.raises(asyncio.CancelledError):
            await worker._run()

        assert state["calls"] == 2  # 异常后确实进入了下一轮


class TestLifecycle:
    """start / stop 生命周期。"""

    async def test_start_and_stop_cancels_task(self, monkeypatch) -> None:
        """start 返回后台 Task，stop 取消该 Task。"""
        redis = FakeZsetRedis([])
        _patch_cache(monkeypatch, redis)
        worker = _make_worker(handler=lambda data: True, interval=60)

        task = worker.start()
        assert task is not None
        await asyncio.sleep(0.05)  # 让循环跑过几轮
        assert task.done() is False

        worker.stop()
        await asyncio.sleep(0.05)
        assert task.cancelled() is True
