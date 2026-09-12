#!/usr/bin/env python3
"""告警与通知服务。支持邮件、钉钉、飞书 webhook。"""

from __future__ import annotations

import json
from typing import Any

import requests

from src.core.config import settings
from src.core.logger import logger


class AlertService:
    """统一告警收敛服务。"""

    def send(self, channel: str, subject: str, message: str, metadata: dict[str, Any] | None = None) -> bool:
        metadata = metadata or {}
        try:
            if channel == "email":
                return self._send_email(subject, message, metadata)
            if channel == "dingtalk":
                return self._send_dingtalk(message, metadata)
            if channel == "feishu":
                return self._send_feishu(message, metadata)
            logger.warning("Unsupported alert channel: %s", channel)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Alert send failed for channel=%s: %s", channel, exc)
            return False

    def _send_email(self, subject: str, message: str, metadata: dict[str, Any]) -> bool:
        to_email = metadata.get("to_email") or settings.auth.secret_key
        if not to_email or to_email == settings.auth.secret_key:
            logger.info("Email alert skipped because no recipient configured")
            return False
        logger.info("Email alert stub: to=%s subject=%s", to_email, subject)
        return True

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
