#!/usr/bin/env python3
"""通知子系统启动装配与重试 Handler 单元测试。

覆盖 src/notification/bootstrap.py：
    - handle_notification_retry：无 provider 丢弃 / 发送成功回写 / 发送失败回写重试 /
      无 delivery_id 不同步状态
    - setup_notification_system：开关关闭直接返回 None / 开关开启装配重试 Worker

数据库、Redis 与重试 Worker 一律 monkeypatch，不触网、不连真实 DB。
"""

from typing import Any

import src.notification.bootstrap as bootstrap_module
from src.notification.bootstrap import handle_notification_retry


class FakeProvider:
    """记录 send 调用、按预设返回值应答的 Provider 替身。"""

    def __init__(self, result: bool) -> None:
        self._result = result
        self.sent: list[Any] = []

    def send(self, message) -> bool:
        self.sent.append(message)
        return self._result


class FakeRegistry:
    """按渠道返回预设 Provider 的注册表替身。"""

    def __init__(self, provider: FakeProvider | None) -> None:
        self._provider = provider

    def get(self, channel: str) -> FakeProvider | None:
        return self._provider


def _base_data(**overrides) -> dict[str, Any]:
    data = {
        "delivery_id": 1,
        "channel": "email",
        "recipient": "a@example.com",
        "subject": "标题",
        "content": "正文",
        "retry_count": 1,
    }
    data.update(overrides)
    return data


class TestHandleNotificationRetry:
    """单条通知重试任务处理行为。"""

    def test_no_provider_drops_task(self, monkeypatch) -> None:
        """渠道无 provider → 直接丢弃，返回 True 出队。"""
        monkeypatch.setattr(bootstrap_module, "get_registry", lambda: FakeRegistry(None))
        assert handle_notification_retry(_base_data()) is True

    def test_send_success_syncs_state(self, monkeypatch) -> None:
        """发送成功 → 回写投递明细为 success，返回 True。"""
        provider = FakeProvider(result=True)
        monkeypatch.setattr(bootstrap_module, "get_registry", lambda: FakeRegistry(provider))
        sync_calls: list[tuple[int, bool]] = []
        monkeypatch.setattr(
            bootstrap_module,
            "_sync_delivery_state",
            lambda delivery_id, success: sync_calls.append((delivery_id, success)),
        )

        assert handle_notification_retry(_base_data(delivery_id=42)) is True
        assert len(provider.sent) == 1
        assert sync_calls == [(42, True)]

    def test_send_failure_syncs_and_keeps(self, monkeypatch) -> None:
        """发送失败 → 回写失败状态，返回 False 保留待下次重试。"""
        provider = FakeProvider(result=False)
        monkeypatch.setattr(bootstrap_module, "get_registry", lambda: FakeRegistry(provider))
        sync_calls: list[tuple[int, bool]] = []
        monkeypatch.setattr(
            bootstrap_module,
            "_sync_delivery_state",
            lambda delivery_id, success: sync_calls.append((delivery_id, success)),
        )

        assert handle_notification_retry(_base_data(delivery_id=7)) is False
        assert sync_calls == [(7, False)]

    def test_no_delivery_id_skips_sync(self, monkeypatch) -> None:
        """无 delivery_id → 发送后不同步投递明细状态。"""
        provider = FakeProvider(result=True)
        monkeypatch.setattr(bootstrap_module, "get_registry", lambda: FakeRegistry(provider))
        called = False

        def _never_sync(**kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr(bootstrap_module, "_sync_delivery_state", _never_sync)

        assert handle_notification_retry(_base_data(delivery_id=None)) is True
        assert called is False


class TestSetupNotificationSystem:
    """通知子系统启动装配分支。"""

    def test_disabled_returns_none(self, monkeypatch) -> None:
        """notification.enabled 关闭 → 跳过装配，返回 None。"""
        monkeypatch.setattr(bootstrap_module.settings.notification, "enabled", False)
        assert bootstrap_module.setup_notification_system() is None

    def test_enabled_starts_worker(self, monkeypatch) -> None:
        """notification.enabled 开启 → 从 DB 重载渠道并启动重试 Worker。"""
        from src.core.config import settings

        monkeypatch.setattr(settings.notification, "enabled", True)

        # 拦截从数据库注册渠道（避免真实 DB）
        reload_called: dict[str, bool] = {}
        monkeypatch.setattr("src.infras.notification.reload_providers_from_db", lambda: reload_called.update(done=True))

        # 伪造 RetryWorker：记录构造参数，start() 返回一个哨兵 Task
        sentinel_task = object()

        class FakeRetryWorker:
            def __init__(self, queue_key, handler, interval_seconds) -> None:
                self.queue_key = queue_key
                self.interval_seconds = interval_seconds

            def start(self):
                return sentinel_task

        monkeypatch.setattr("src.scheduling.retry_worker.RetryWorker", FakeRetryWorker)

        result = bootstrap_module.setup_notification_system()
        assert reload_called.get("done") is True
        assert result is sentinel_task
