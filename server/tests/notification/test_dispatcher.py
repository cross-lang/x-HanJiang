#!/usr/bin/env python3
"""
通知调度器测试

测试订阅驱动调度链路的关键行为：
    - dispatch_for_user：订阅即路由（勾选渠道即发送渠道，不受 DEFAULT_ROUTES 白名单限制）
    - dispatch：webhook 型渠道（钉钉/飞书）按接收方 URL 临时构造 Provider，
      不复用 registry 中指向系统级 webhook 的 Provider
    - 非 webhook 渠道（邮件）仍走 registry Provider
"""

from typing import Any

import src.notification.dispatcher as dispatcher_module
from src.notification.dispatcher import NotificationDispatcher


class FakeConfigRepository:
    """内存版配置仓库替身，返回预设的接收方映射。"""

    def __init__(self, recipients: dict[str, str]) -> None:
        self._recipients = recipients

    def build_recipients_map(self, user_id: int, event_type: str) -> dict[str, str]:
        return dict(self._recipients)


class FakeRegistry:
    """内存版渠道注册表替身。"""

    def __init__(self, providers: dict[str, Any] | None = None) -> None:
        self._providers = providers or {}
        self.asked: list[str] = []

    def get(self, channel: str):
        self.asked.append(channel)
        return self._providers.get(channel)


class FakeWebhookProvider:
    """捕获构造参数的 webhook Provider 替身（替代钉钉/飞书真实 Provider）。"""

    instances: list["FakeWebhookProvider"] = []

    def __init__(self, webhook_url: str = "", **kwargs: Any) -> None:
        self.webhook_url = webhook_url
        self.sent: list[Any] = []
        FakeWebhookProvider.instances.append(self)

    def send(self, message: Any) -> bool:
        self.sent.append(message)
        return True


class FakeEmailProvider:
    """邮件 Provider 替身，验证 registry Provider 被复用。"""

    def __init__(self) -> None:
        self.sent: list[Any] = []

    def send(self, message: Any) -> bool:
        self.sent.append(message)
        return True


def _build_dispatcher(recipients: dict[str, str], registry: FakeRegistry) -> NotificationDispatcher:
    return NotificationDispatcher(registry=registry, session=None)


class TestDispatchForUser:
    """订阅即路由行为。"""

    def test_subscribed_channel_bypasses_default_routes(self, monkeypatch) -> None:
        """钉钉不在 user.profile_updated 的 DEFAULT_ROUTES 白名单里，但用户已订阅 → 必须发送。"""
        monkeypatch.setattr(
            dispatcher_module,
            "UserNotificationConfigRepository",
            lambda session: FakeConfigRepository({"dingtalk": "https://oapi.dingtalk.com/robot/send?access_token=abc"}),
        )
        monkeypatch.setattr(dispatcher_module, "_WEBHOOK_CHANNEL_PROVIDER_CLASSES", {"dingtalk": FakeWebhookProvider})
        FakeWebhookProvider.instances = []
        registry = FakeRegistry()  # registry 中没有钉钉 Provider，也不应影响个人 webhook 发送
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch_for_user(
            user_id=5,
            event_type="user.profile_updated",
            pre_rendered=("资料变更", "你的资料已更新"),
        )

        assert len(deliveries) == 1
        assert deliveries[0].channel == "dingtalk"
        assert deliveries[0].status == "success"
        assert len(FakeWebhookProvider.instances) == 1
        assert FakeWebhookProvider.instances[0].webhook_url == "https://oapi.dingtalk.com/robot/send?access_token=abc"

    def test_unsubscribed_user_falls_back_to_station(self, monkeypatch) -> None:
        """无任何订阅 → 回退默认站内信发送（保证"默认勾选=真实投递"），不经 registry。"""
        monkeypatch.setattr(
            dispatcher_module, "UserNotificationConfigRepository", lambda session: FakeConfigRepository({})
        )
        registry = FakeRegistry()
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch_for_user(user_id=5, event_type="user.profile_updated")

        assert len(deliveries) == 1
        assert deliveries[0].channel == "station"
        assert deliveries[0].recipient == "user:5"
        assert deliveries[0].status == "success"
        assert registry.asked == []


class TestDispatchProviderSelection:
    """dispatch 的 Provider 选择行为。"""

    def test_webhook_channel_builds_provider_per_recipient(self, monkeypatch) -> None:
        """显式指定钉钉渠道时，按接收方 URL 构造 Provider，而非 registry 中的系统级 Provider。"""
        monkeypatch.setattr(dispatcher_module, "_WEBHOOK_CHANNEL_PROVIDER_CLASSES", {"dingtalk": FakeWebhookProvider})
        FakeWebhookProvider.instances = []
        system_provider = FakeWebhookProvider(webhook_url="https://system.webhook")
        FakeWebhookProvider.instances = []  # 清掉系统级 Provider 的构造记录，只统计 dispatch 内新建的
        registry = FakeRegistry({"dingtalk": system_provider})
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch(
            event_type="user.profile_updated",
            recipients={"dingtalk": "https://personal.webhook/abc"},
            channels=["dingtalk"],
            pre_rendered=("资料变更", "你的资料已更新"),
        )

        assert deliveries[0].status == "success"
        # 系统级 Provider 未被调用，新构造的个人 Provider 收到了消息
        assert system_provider.sent == []
        assert len(FakeWebhookProvider.instances) == 1
        assert FakeWebhookProvider.instances[0].webhook_url == "https://personal.webhook/abc"

    def test_email_channel_uses_registry_provider(self, monkeypatch) -> None:
        """非 webhook 渠道：复用 registry 中的邮件 Provider。"""
        email_provider = FakeEmailProvider()
        registry = FakeRegistry({"email": email_provider})
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch(
            event_type="user.profile_updated",
            recipients={"email": "user@example.com"},
            channels=["email"],
            pre_rendered=("资料变更", "你的资料已更新"),
        )

        assert deliveries[0].status == "success"
        assert len(email_provider.sent) == 1

    def test_station_channel_bypasses_registry(self, monkeypatch) -> None:
        """站内信渠道：不经外部 Provider/registry，由 dispatcher 收件箱路径处理。"""
        station_provider = FakeEmailProvider()
        registry = FakeRegistry({"station": station_provider})
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch(
            event_type="user.profile_updated",
            recipients={"station": "user:5"},
            channels=["station"],
            pre_rendered=("资料变更", "你的资料已更新"),
        )

        assert deliveries[0].status == "success"
        assert deliveries[0].recipient == "user:5"
        assert registry.asked == []  # 未查询 registry
        assert len(station_provider.sent) == 0  # registry Provider 未被调用


class TestEmptyTemplateDefense:
    """模板段缺失时的渠道跳过行为（防止空消息/空邮件/failed 投递）。"""

    def test_empty_render_skips_channel_without_sending(self, monkeypatch) -> None:
        """渲染结果为空：该渠道整体跳过，不调用 provider、不产生投递明细。"""
        monkeypatch.setattr(dispatcher_module, "render_template", lambda *a, **kw: ("", ""))
        email_provider = FakeEmailProvider()
        registry = FakeRegistry({"email": email_provider})
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch(
            event_type="user.profile_updated",
            recipients={"email": "user@example.com"},
            channels=["email"],
        )

        assert deliveries == []
        assert email_provider.sent == []

    def test_pre_rendered_bypasses_template_check(self) -> None:
        """pre_rendered 直传内容不受空模板检查影响（系统通知广播场景）。"""
        email_provider = FakeEmailProvider()
        registry = FakeRegistry({"email": email_provider})
        dispatcher = _build_dispatcher({}, registry)

        deliveries = dispatcher.dispatch(
            event_type="system.notice",
            recipients={"email": "user@example.com"},
            channels=["email"],
            pre_rendered=("维护通知", "今晚 22:00 系统维护"),
        )

        assert deliveries[0].status == "success"
        assert len(email_provider.sent) == 1
