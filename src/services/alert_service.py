#!/usr/bin/env python3
"""系统告警分发服务，支持邮件、钉钉和飞书 webhook。"""

from __future__ import annotations

import json
from typing import Any

import requests

from src.constants.enums import AlertChannel
from src.core.config import settings
from src.core.logger import logger
from src.infras.email import EmailService


class AlertService:
    """统一系统告警服务。"""

    def send(
        self,
        channel: AlertChannel | str,
        subject: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        metadata = metadata or {}
        try:
            channel = AlertChannel(channel)
            if channel is AlertChannel.EMAIL:
                return self._send_email(subject, message, metadata)
            if channel is AlertChannel.DINGTALK:
                return self._send_dingtalk(message, metadata)
            if channel is AlertChannel.FEISHU:
                return self._send_feishu(message, metadata)
            logger.warning("Unsupported alert channel: %s", channel)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Alert send failed for channel=%s: %s", channel, exc)
            return False

    def _send_email(self, subject: str, message: str, metadata: dict[str, Any]) -> bool:
        to_email = metadata.get("to_email")
        if not to_email:
            logger.info("Email alert skipped because no recipient configured")
            return False

        html_content = metadata.get("html_content") or message
        text_content = metadata.get("text_content") or message
        return EmailService().send_email(
            to_address=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def _send_dingtalk(self, message: str, metadata: dict[str, Any]) -> bool:
        webhook_url = metadata.get("webhook_url") or settings.redis.url
        if not webhook_url or webhook_url == settings.redis.url:
            logger.info("DingTalk alert skipped because no webhook configured")
            return False
        payload = {"msgtype": "text", "text": {"content": message}}
        response = requests.post(webhook_url, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        return True

    def _send_feishu(self, message: str, metadata: dict[str, Any]) -> bool:
        webhook_url = metadata.get("webhook_url") or settings.database.url
        if not webhook_url or webhook_url == settings.database.url:
            logger.info("Feishu alert skipped because no webhook configured")
            return False
        payload = {"msg_type": "text", "content": {"text": message}}
        response = requests.post(webhook_url, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        return True
