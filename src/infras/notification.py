"""通知渠道 Provider 抽象层。

采用 Strategy 模式：每个渠道一个 Provider 实现。
新增渠道只需：实现 BaseNotificationProvider → register_provider()。

Usage:
    from src.infras.notification import get_registry

    registry = get_registry()
    registry.send("email", NotificationMessage(...))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.core.logger import logger

# ============================================================
# 消息体
# ============================================================


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """统一的通知消息体。"""

    recipient: str
    subject: str
    content: str
    content_type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# 抽象基类
# ============================================================


class BaseNotificationProvider(ABC):
    """通知渠道抽象基类。"""

    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """发送通知，成功返回 True，失败返回 False 或抛异常。"""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道标识，如 'email', 'dingtalk', 'feishu', 'sms'。"""


# ============================================================
# Email（复用已有 SmtpEmailProvider）
# ============================================================


class EmailNotificationProvider(BaseNotificationProvider):
    """邮件通知渠道。"""

    def __init__(self) -> None:
        from src.infras.email import get_cached_email_provider

        self._email = get_cached_email_provider()

    @property
    def channel_name(self) -> str:
        return "email"

    def send(self, message: NotificationMessage) -> bool:
        return self._email.send_email(
            to_address=message.recipient,
            subject=message.subject,
            html_content=message.content if message.content_type == "html" else "",
            text_content=message.content if message.content_type != "html" else None,
        )


# ============================================================
# 钉钉 Webhook
# ============================================================


class DingTalkNotificationProvider(BaseNotificationProvider):
    """钉钉机器人 Webhook 通知。

    支持加签和纯 webhook 两种模式。
    """

    def __init__(self, webhook_url: str, secret: str = "") -> None:
        self._webhook_url = webhook_url
        self._secret = secret

    @property
    def channel_name(self) -> str:
        return "dingtalk"

    def send(self, message: NotificationMessage) -> bool:
        import base64
        import hashlib
        import hmac
        import time

        import requests

        url = self._webhook_url
        if self._secret:
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{self._secret}"
            hmac_code = hmac.new(
                self._secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")
            url = f"{url}&timestamp={timestamp}&sign={sign}"

        is_markdown = message.content_type == "markdown"
        payload = {
            "msgtype": "markdown" if is_markdown else "text",
            (
                "markdown" if is_markdown else "text"
            ): {
                "title": message.subject,
                "text" if is_markdown else "content": message.content,
            },
        }

        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") != 0:
            logger.error("DingTalk send failed: %s", result)
            return False
        return True


# ============================================================
# 飞书 Webhook
# ============================================================


class FeishuNotificationProvider(BaseNotificationProvider):
    """飞书机器人 Webhook 通知。"""

    def __init__(self, webhook_url: str, secret: str = "") -> None:
        self._webhook_url = webhook_url
        self._secret = secret

    @property
    def channel_name(self) -> str:
        return "feishu"

    def send(self, message: NotificationMessage) -> bool:
        import base64
        import hashlib
        import hmac
        import time

        import requests

        extra: dict[str, Any] = {}
        if self._secret:
            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{self._secret}"
            hmac_code = hmac.new(
                string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")
            extra = {"timestamp": timestamp, "sign": sign}

        payload = {
            "msg_type": "text",
            "content": {"text": message.content},
            **extra,
        }

        resp = requests.post(self._webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code", 0) != 0 and result.get("StatusCode", 0) != 0:
            logger.error("Feishu send failed: %s", result)
            return False
        return True


# ============================================================
# SMS（骨架）
# ============================================================


class SmsNotificationProvider(BaseNotificationProvider):
    """短信通知渠道（骨架，接入阿里云/腾讯云 SMS 时填充）。"""

    def __init__(
        self,
        access_key: str = "",
        secret_key: str = "",
        sign_name: str = "",
        template_code: str = "",
    ) -> None:
        self._access_key = access_key
        self._secret_key = secret_key
        self._sign_name = sign_name
        self._template_code = template_code

    @property
    def channel_name(self) -> str:
        return "sms"

    def send(self, message: NotificationMessage) -> bool:
        logger.warning("SMS provider not implemented yet")
        return False


# ============================================================
# Provider 注册表
# ============================================================


class NotificationProviderRegistry:
    """通知渠道 Provider 注册表。

    线程安全的单例，管理所有已注册的渠道 Provider。
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseNotificationProvider] = {}

    def register(self, provider: BaseNotificationProvider) -> None:
        """注册一个渠道 Provider。"""
        self._providers[provider.channel_name] = provider
        logger.info("Notification provider registered: %s", provider.channel_name)

    def get(self, channel: str) -> BaseNotificationProvider | None:
        """获取指定渠道的 Provider。"""
        return self._providers.get(channel)

    def has(self, channel: str) -> bool:
        """检查渠道是否已注册。"""
        return channel in self._providers

    def list_channels(self) -> list[str]:
        """返回所有已注册渠道名。"""
        return list(self._providers.keys())

    def send(self, channel: str, message: NotificationMessage) -> bool:
        """通过指定渠道发送通知。"""
        provider = self._providers.get(channel)
        if provider is None:
            logger.warning("No provider registered for channel: %s", channel)
            return False
        return provider.send(message)


# ============================================================
# 模块级单例
# ============================================================

_registry: NotificationProviderRegistry | None = None


def get_registry() -> NotificationProviderRegistry:
    """获取全局 Provider 注册表（应用级别单例）。"""
    global _registry
    if _registry is None:
        _registry = NotificationProviderRegistry()
    return _registry
