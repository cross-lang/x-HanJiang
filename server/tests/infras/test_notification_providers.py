#!/usr/bin/env python3
"""通知渠道 Provider 单元测试。

覆盖 src/infras/notification.py 中各渠道的发送分支：
    - Email：委托底层 EmailProvider，按 content_type 区分 html/text 参数
    - DingTalk：工作通知模式 / Webhook 降级模式 / 加签 / 失败回包 / 无配置兜底
    - Feishu：应用消息模式 / Webhook 降级模式 / 加签 / token 失败 / 无配置兜底
    - Sms：骨架实现（恒返回 False）
    - ProviderRegistry：注册/查询/发送/缺失渠道兜底
    - get_registry 单例、register_default_providers 配置分支

所有外部 HTTP / SMTP 一律经 FakeHttpProvider / FakeEmailProvider 注入，不触网。
"""

from typing import Any

import src.infras.notification as notify_module
from src.infras.notification import (
    DingTalkNotificationProvider,
    EmailNotificationProvider,
    FeishuNotificationProvider,
    NotificationMessage,
    NotificationProviderRegistry,
    SmsNotificationProvider,
    register_default_providers,
)


class FakeHttpProvider:
    """记录 POST 调用、按预设返回值应答的 HTTP 替身。"""

    def __init__(self, script: list[dict[str, Any]] | None = None) -> None:
        # script 为按调用顺序的应答列表；命中即弹出，未命中返回空 dict
        self.script: list[dict[str, Any]] = list(script or [])
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, json: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        self.calls.append({"url": url, "json": json, "kwargs": kwargs})
        if self.script:
            return self.script.pop(0)
        return {}


class FakeEmailProvider:
    """记录 send_email 调用的邮件替身。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_email(self, to_address: str, subject: str, html_content: str, text_content: str | None = None) -> bool:
        self.calls.append(
            {
                "to": to_address,
                "subject": subject,
                "html": html_content,
                "text": text_content,
            }
        )
        return True


def _msg(recipient: str = "user001", content: str = "告警内容", content_type: str = "text") -> NotificationMessage:
    return NotificationMessage(recipient=recipient, subject="标题", content=content, content_type=content_type)


# ── 邮件渠道 ──────────────────────────────────────────


class TestEmailProvider:
    """EmailNotificationProvider 委托行为。"""

    def test_channel_name(self) -> None:
        provider = EmailNotificationProvider(email_provider=FakeEmailProvider())
        assert provider.channel_name == "email"

    def test_text_content_sends_text_body(self) -> None:
        """纯文本消息 → text_content 携带正文、html_content 为空。"""
        fake = FakeEmailProvider()
        provider = EmailNotificationProvider(email_provider=fake)

        ok = provider.send(_msg(content_type="text"))

        assert ok is True
        assert fake.calls[0]["to"] == "user001"
        assert fake.calls[0]["text"] == "告警内容"
        assert fake.calls[0]["html"] == ""

    def test_html_content_sends_html_body(self) -> None:
        """html 消息 → html_content 携带正文、text_content 为 None。"""
        fake = FakeEmailProvider()
        provider = EmailNotificationProvider(email_provider=fake)

        provider.send(_msg(content_type="html"))

        assert fake.calls[0]["html"] == "告警内容"
        assert fake.calls[0]["text"] is None


# ── 钉钉渠道 ──────────────────────────────────────────


class TestDingTalkProvider:
    """钉钉双模式发送分支。"""

    def test_channel_name(self) -> None:
        provider = DingTalkNotificationProvider(http_provider=FakeHttpProvider())
        assert provider.channel_name == "dingtalk"

    def test_work_notification_success(self) -> None:
        """工作通知模式：先取 token，再发会话消息，无 errorCode 即成功。"""
        http = FakeHttpProvider(
            script=[
                {"accessToken": "tok-1", "expireIn": 7200},  # 取 token
                {},  # 发送消息回包（无 errorCode）
            ]
        )
        provider = DingTalkNotificationProvider(app_key="ak", app_secret="as", agent_id="aid", http_provider=http)

        assert provider.send(_msg(recipient="user001")) is True
        # 第一次调用 token 接口，第二次调用发消息接口
        assert "accessToken" in http.calls[0]["url"]
        assert "sendToConversation" in http.calls[1]["url"]

    def test_work_notification_caches_token(self) -> None:
        """token 未过期前复用，不重复请求 accessToken。"""
        http = FakeHttpProvider(script=[{"accessToken": "tok-1", "expireIn": 7200}, {}, {}])
        provider = DingTalkNotificationProvider(app_key="ak", app_secret="as", agent_id="aid", http_provider=http)
        provider.send(_msg(recipient="u1"))
        provider.send(_msg(recipient="u2"))

        token_calls = [c for c in http.calls if "accessToken" in c["url"]]
        assert len(token_calls) == 1  # 仅首次取 token

    def test_work_notification_error_code_returns_false(self) -> None:
        """工作通知回包含 errorCode → 发送失败。"""
        http = FakeHttpProvider(script=[{"accessToken": "tok-1", "expireIn": 7200}, {"errorCode": 88, "errmsg": "bad"}])
        provider = DingTalkNotificationProvider(app_key="ak", app_secret="as", agent_id="aid", http_provider=http)
        assert provider.send(_msg(recipient="u1")) is False

    def test_webhook_mode_success(self) -> None:
        """无应用凭证、有 webhook → Webhook 群聊降级，errcode=0 成功。"""
        http = FakeHttpProvider(script=[{"errcode": 0}])
        provider = DingTalkNotificationProvider(webhook_url="https://robot.example/send", http_provider=http)
        assert provider.send(_msg(recipient="")) is True
        assert http.calls[0]["url"].startswith("https://robot.example/send")

    def test_webhook_mode_with_secret_signs_url(self) -> None:
        """配置 secret → webhook URL 追加 timestamp 与 sign。"""
        http = FakeHttpProvider(script=[{"errcode": 0}])
        provider = DingTalkNotificationProvider(
            webhook_url="https://robot.example/send?access_token=x",
            secret="SEC",
            http_provider=http,
        )
        provider.send(_msg(recipient=""))

        posted_url = http.calls[0]["url"]
        assert "timestamp=" in posted_url
        assert "sign=" in posted_url

    def test_webhook_mode_error_code_returns_false(self) -> None:
        """Webhook 回包 errcode!=0 → 失败。"""
        http = FakeHttpProvider(script=[{"errcode": 30001, "errmsg": "invalid"}])
        provider = DingTalkNotificationProvider(webhook_url="https://robot.example/send", http_provider=http)
        assert provider.send(_msg(recipient="")) is False

    def test_no_config_returns_false(self) -> None:
        """既无应用凭证也无 webhook → 直接失败。"""
        provider = DingTalkNotificationProvider(http_provider=FakeHttpProvider())
        assert provider.send(_msg()) is False


# ── 飞书渠道 ──────────────────────────────────────────


class TestFeishuProvider:
    """飞书双模式发送分支。"""

    def test_channel_name(self) -> None:
        provider = FeishuNotificationProvider(http_provider=FakeHttpProvider())
        assert provider.channel_name == "feishu"

    def test_app_message_success(self) -> None:
        """应用消息模式：先取 tenant_token，再发消息，code=0 成功。"""
        http = FakeHttpProvider(
            script=[
                {"code": 0, "tenant_access_token": "ftok", "expire": 7200},
                {"code": 0, "data": {"message_id": "m1"}},
            ]
        )
        provider = FeishuNotificationProvider(app_id="aid", app_secret="asecret", http_provider=http)
        assert provider.send(_msg(recipient="ou_123")) is True
        assert "tenant_access_token" in http.calls[0]["url"]
        assert "/im/v1/messages" in http.calls[1]["url"]

    def test_app_message_token_error_raises(self) -> None:
        """token 接口 code!=0 → 抛 RuntimeError。"""
        http = FakeHttpProvider(script=[{"code": 999, "msg": "bad credentials"}])
        provider = FeishuNotificationProvider(app_id="aid", app_secret="asecret", http_provider=http)
        import pytest

        with pytest.raises(RuntimeError):
            provider.send(_msg(recipient="ou_123"))

    def test_app_message_error_code_returns_false(self) -> None:
        """发消息回包 code!=0 → 失败。"""
        http = FakeHttpProvider(script=[{"code": 0, "tenant_access_token": "ftok", "expire": 7200}, {"code": 230002}])
        provider = FeishuNotificationProvider(app_id="aid", app_secret="asecret", http_provider=http)
        assert provider.send(_msg(recipient="ou_123")) is False

    def test_webhook_mode_success(self) -> None:
        """无应用凭证、有 webhook → Webhook 降级，code=0 成功。"""
        http = FakeHttpProvider(script=[{"code": 0, "msg": "success"}])
        provider = FeishuNotificationProvider(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/abc", http_provider=http
        )
        assert provider.send(_msg(recipient="")) is True

    def test_webhook_mode_status_code_zero_success(self) -> None:
        """飞书 webhook 成功回包也可能用 StatusCode=0 表示。"""
        http = FakeHttpProvider(script=[{"StatusCode": 0, "data": {}}])
        provider = FeishuNotificationProvider(webhook_url="https://hook/abc", http_provider=http)
        assert provider.send(_msg(recipient="")) is True

    def test_webhook_mode_with_secret(self) -> None:
        """配置 secret → 载荷中携带 timestamp 与 sign。"""
        http = FakeHttpProvider(script=[{"code": 0}])
        provider = FeishuNotificationProvider(webhook_url="https://hook/abc", secret="FSEC", http_provider=http)
        provider.send(_msg(recipient=""))

        payload = http.calls[0]["json"]
        assert "timestamp" in payload
        assert "sign" in payload

    def test_webhook_mode_failure(self) -> None:
        """code 与 StatusCode 均非 0 → 失败。"""
        http = FakeHttpProvider(script=({"code": 19021, "StatusCode": 1},))
        provider = FeishuNotificationProvider(webhook_url="https://hook/abc", http_provider=http)
        assert provider.send(_msg(recipient="")) is False

    def test_no_config_returns_false(self) -> None:
        """既无应用凭证也无 webhook → 直接失败。"""
        provider = FeishuNotificationProvider(http_provider=FakeHttpProvider())
        assert provider.send(_msg()) is False


# ── 短信渠道 ──────────────────────────────────────────


class TestSmsProvider:
    """SmsNotificationProvider 骨架实现。"""

    def test_channel_name(self) -> None:
        assert SmsNotificationProvider().channel_name == "sms"

    def test_send_not_implemented_returns_false(self) -> None:
        assert SmsNotificationProvider(access_key="ak").send(_msg()) is False


# ── 注册表 ────────────────────────────────────────────


class TestRegistry:
    """NotificationProviderRegistry 行为。"""

    def test_register_get_has_list(self) -> None:
        registry = NotificationProviderRegistry()
        email = EmailNotificationProvider(email_provider=FakeEmailProvider())
        registry.register(email)

        assert registry.has("email") is True
        assert registry.get("email") is email
        assert registry.list_channels() == ["email"]
        assert registry.has("sms") is False

    def test_send_uses_provider(self) -> None:
        registry = NotificationProviderRegistry()
        email = EmailNotificationProvider(email_provider=FakeEmailProvider())
        registry.register(email)
        assert registry.send("email", _msg()) is True

    def test_send_missing_channel_returns_false(self) -> None:
        registry = NotificationProviderRegistry()
        assert registry.send("sms", _msg()) is False


# ── 工厂函数 ──────────────────────────────────────────


class TestFactory:
    """get_registry 单例与 register_default_providers 配置分支。"""

    def test_get_registry_singleton(self) -> None:
        from src.infras.notification import get_registry

        assert get_registry() is get_registry()

    @staticmethod
    def _patch_channels(monkeypatch, **overrides) -> None:
        """统一覆盖 settings.notification 上的渠道开关字段。"""
        from src.core.config import settings

        for name, value in {
            "dingtalk_webhook": "",
            "dingtalk_app_key": "",
            "feishu_webhook": "",
            "feishu_app_id": "",
            "sms_access_key": "",
            **overrides,
        }.items():
            monkeypatch.setattr(settings.notification, name, value)

    def test_register_default_providers_email_always(self, monkeypatch) -> None:
        """邮件渠道始终注册；钉钉/飞书/短信无配置时不注册。"""
        fresh = NotificationProviderRegistry()
        monkeypatch.setattr(notify_module, "_registry", fresh)
        self._patch_channels(monkeypatch)

        registry = register_default_providers()
        assert registry.list_channels() == ["email"]

    def test_register_default_providers_optional_channels(self, monkeypatch) -> None:
        """钉钉/飞书/短信任一配置存在即注册对应渠道。"""
        fresh = NotificationProviderRegistry()
        monkeypatch.setattr(notify_module, "_registry", fresh)
        self._patch_channels(
            monkeypatch,
            dingtalk_webhook="https://robot/x",
            feishu_app_id="fid",
            sms_access_key="sak",
        )

        registry = register_default_providers()
        channels = set(registry.list_channels())
        assert channels == {"email", "dingtalk", "feishu", "sms"}
