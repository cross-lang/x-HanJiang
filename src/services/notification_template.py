"""通知模板管理。

模板存储在 YAML 文件中，支持变量插值。
按 event_type + channel 组合查找模板。

模板文件示例 (config/notification_templates/user_events.yaml):
    user.registered:
      email:
        subject: "欢迎注册，{username}！"
        content: "您好 {username}，欢迎加入。"
      dingtalk:
        subject: "新用户注册"
        content: "用户 {username} 已注册"
"""

from __future__ import annotations

from typing import Any

import yaml

from src.core.logger import logger
from src.utils.helpers import find_project_root

_TEMPLATE_DIR = find_project_root() / "config" / "notification_templates"

_templates: dict[str, Any] | None = None


def _load_templates() -> dict[str, Any]:
    """加载所有通知模板文件。"""
    global _templates
    if _templates is not None:
        return _templates

    _templates = {}
    if not _TEMPLATE_DIR.exists():
        logger.warning("Notification template dir not found: %s", _TEMPLATE_DIR)
        return _templates

    for f in _TEMPLATE_DIR.glob("*.yaml"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = yaml.safe_load(fp) or {}
            if isinstance(data, dict):
                _templates.update(data)
        except Exception as exc:
            logger.warning("Failed to load template %s: %s", f, exc)

    return _templates


def reload_templates() -> None:
    """强制重新加载模板（用于热更新）。"""
    global _templates
    _templates = None
    _load_templates()


def render_template(
    event_type: str,
    channel: str,
    variables: dict[str, Any],
) -> tuple[str, str]:
    """渲染通知模板。

    查找顺序：event_type.channel → event_type.default → 空模板。

    Returns:
        (subject, content) 渲染后的主题和正文
    """
    templates = _load_templates()

    event_templates = templates.get(event_type, {})
    channel_template = event_templates.get(
        channel, event_templates.get("default", {})
    )

    if not channel_template:
        logger.warning(
            "No template found for event=%s channel=%s", event_type, channel
        )
        return "", ""

    subject = str(channel_template.get("subject", ""))
    content = str(channel_template.get("content", ""))

    try:
        subject = subject.format(**variables)
        content = content.format(**variables)
    except KeyError as exc:
        logger.warning(
            "Template variable missing: %s for event=%s channel=%s",
            exc,
            event_type,
            channel,
        )

    return subject, content
