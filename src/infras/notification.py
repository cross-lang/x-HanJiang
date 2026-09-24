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
# 钉钉（支持工作通知 per-user + Webhook 群聊降级）
# ============================================================


class DingTalkNotificationProvider(BaseNotificationProvider):
    """钉钉通知渠道。

    双模式：
    - 工作通知模式（推荐）：配置 app_key + app_secret + agent_id，
      通过钉钉 OpenAPI 向指定 userid 发送工作通知，实现 per-user 投递。
    - Webhook 模式（降级）：仅配置 webhook_url，向群机器人所在群广播。
    """

    def __init__(
        self,
        webhook_url: str = "",
        secret: str = "",
        app_key: str = "",
        app_secret: str = "",
        agent_id: str = "",
    ) -> None:
        self._webhook_url = webhook_url
        self._secret = secret
        self._app_key = app_key
        self._app_secret = app_secret
        self._agent_id = agent_id
        self._access_token: str = ""
        self._token_expires_at: float = 0

    @property
    def channel_name(self) -> str:
        return "dingtalk"

    @property
    def _use_work_notification(self) -> bool:
        """是否使用工作通知模式（需要应用凭证 + recipient 非空）。"""
        return bool(self._app_key and self._app_secret and self._agent_id)

    def _get_access_token(self) -> str:
        """获取钉钉企业内部应用 access_token（自动缓存，过期前 5 分钟刷新）。"""
        import time

        import requests

        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        resp = requests.post(
            "https://api.dingtalk.com/v1.0/oauth2/accessToken",
            json={"appKey": self._app_key, "appSecret": self._app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["accessToken"]
        # expiresIn 单位秒，提前 5 分钟刷新
        self._token_expires_at = time.time() + data["expireIn"] - 300
        return self._access_token

    def send(self, message: NotificationMessage) -> bool:
        import requests

        # 有应用凭证且有接收人 → 工作通知
        if self._use_work_notification and message.recipient:
            return self._send_work_notification(message)

        # 降级到 Webhook 群聊
        if self._webhook_url:
            return self._send_webhook(message)

        logger.error(
            "DingTalk send skipped: neither work-notification credentials "
            "nor webhook_url configured"
        )
        return False

    def _send_work_notification(self, message: NotificationMessage) -> bool:
        """通过工作通知 API 发送给指定用户。"""
        import requests

        token = self._get_access_token()
        url = (
            "https://api.dingtalk.com/v1.0/org/corpversations/"
            "messages/sendToConversation"
        )
        headers = {"x-acs-dingtalk-access-token": token}
        payload = {
            "agentId": self._agent_id,
            "useridList": message.recipient,
            "msg": {
                "msgtype": "text",
                "text": {"content": message.content},
            },
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if "errorCode" in result:
            logger.error("DingTalk work notification failed: %s", result)
            return False
        return True

    def _send_webhook(self, message: NotificationMessage) -> bool:
        """通过 Webhook 发送到群聊（降级模式）。"""
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

        payload = {
            "msgtype": "text",
            "text": {"content": message.content},
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") != 0:
            logger.error("DingTalk webhook failed: %s", result)
            return False
        return True


# ============================================================
# 飞书（支持应用消息 per-user + Webhook 群聊降级）
# ============================================================


class FeishuNotificationProvider(BaseNotificationProvider):
    """飞书通知渠道。

    双模式：
    - 应用消息模式（推荐）：配置 app_id + app_secret，
      通过飞书 OpenAPI 向指定 open_id 发送应用消息，实现 per-user 投递。
    - Webhook 模式（降级）：仅配置 webhook_url，向群机器人所在群广播。
    """

    def __init__(
        self,
        webhook_url: str = "",
        secret: str = "",
        app_id: str = "",
        app_secret: str = "",
    ) -> None:
        self._webhook_url = webhook_url
        self._secret = secret
        self._app_id = app_id
        self._app_secret = app_secret
        self._tenant_token: str = ""
        self._token_expires_at: float = 0

    @property
    def channel_name(self) -> str:
        return "feishu"

    @property
    def _use_app_message(self) -> bool:
        """是否使用应用消息模式（需要应用凭证 + recipient 非空）。"""
        return bool(self._app_id and self._app_secret)

    def _get_tenant_token(self) -> str:
        """获取飞书 tenant_access_token（自动缓存，过期前 5 分钟刷新）。"""
        import time

        import requests

        if self._tenant_token and time.time() < self._token_expires_at:
            return self._tenant_token

        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu token error: {data}")
        self._tenant_token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data["expire"] - 300
        return self._tenant_token

    def send(self, message: NotificationMessage) -> bool:
        import requests

        # 有应用凭证且有接收人 → 应用消息
        if self._use_app_message and message.recipient:
            return self._send_app_message(message)

        # 降级到 Webhook 群聊
        if self._webhook_url:
            return self._send_webhook(message)

        logger.error(
            "Feishu send skipped: neither app credentials "
            "nor webhook_url configured"
        )
        return False

    def _send_app_message(self, message: NotificationMessage) -> bool:
        """通过应用消息 API 发送给指定用户（open_id）。"""
        import requests

        token = self._get_tenant_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"receive_id_type": "open_id"}
        payload = {
            "receive_id": message.recipient,
            "msg_type": "text",
            "content": '{"text": ' + f'"{message.content}"' + '}',
        }
        resp = requests.post(
            url, json=payload, headers=headers, params=params, timeout=10
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code", 0) != 0:
            logger.error("Feishu app message failed: %s", result)
            return False
        return True

    def _send_webhook(self, message: NotificationMessage) -> bool:
        """通过 Webhook 发送到群聊（降级模式）。"""
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
            logger.error("Feishu webhook failed: %s", result)
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
