#!/usr/bin/env python3
"""通知模板完整性测试。

锁定约束，防止再次出现空模板/漏模板导致渲染空消息：
    - 个人可订阅事件 × 4 个个人渠道（站内信/邮件/钉钉/飞书）：模板段齐全且非空
    - 系统告警：模板四段就绪
    - 验证码仅邮件；直传/直写型事件无需模板
    - 事件键不得跨文件重复、不得出现枚举之外的拼写
"""

import yaml
from src.constants.notification import (
    PERSONAL_SUBSCRIBABLE_CHANNELS,
    PERSONAL_SUBSCRIBABLE_EVENTS,
    NotificationEvent,
)
from src.notification import template as template_module

# 模板四段就绪的非个人订阅事件（系统级渠道）
_FOUR_SECTION_EVENTS = {
    NotificationEvent.SYSTEM_ALERT,
}

# 无需模板的事件：pre_rendered 直传内容 / 直写入库 / 仅邮件的验证码
_NO_TEMPLATE_EVENTS = {
    NotificationEvent.SYSTEM_NOTICE,
    NotificationEvent.STATION_MESSAGE,
}
_EMAIL_ONLY_EVENTS = {NotificationEvent.SECURITY_VERIFY_CODE}


def _load_all_templates() -> dict[str, dict]:
    templates = template_module._load_templates()
    return {key: body for key, body in templates.items() if isinstance(body, dict)}


class TestTemplateCoverage:
    """已派发事件与模板段的覆盖完整性。"""

    def test_personal_events_have_all_four_channel_sections(self) -> None:
        """个人可订阅事件 × 4 个个人渠道：每段 subject/content 非空。"""
        templates = _load_all_templates()
        problems = []
        for event in PERSONAL_SUBSCRIBABLE_EVENTS:
            body = templates.get(event.value)
            if not body:
                problems.append(f"{event.value}: 整个事件段缺失")
                continue
            for channel in PERSONAL_SUBSCRIBABLE_CHANNELS:
                section = body.get(channel.mark)
                if not section:
                    problems.append(f"{event.value}.{channel.mark}: 渠道段缺失")
                elif not str(section.get("subject", "")).strip() or not str(section.get("content", "")).strip():
                    problems.append(f"{event.value}.{channel.mark}: subject/content 为空")
        assert problems == [], "个人订阅事件模板缺段:\n" + "\n".join(problems)

    def test_system_events_have_four_sections(self) -> None:
        """系统告警：站内信/邮件/钉钉/飞书四段就绪。"""
        templates = _load_all_templates()
        required = ["station", "email", "dingtalk", "feishu"]
        problems = []
        for event in _FOUR_SECTION_EVENTS:
            body = templates.get(event.value)
            if not body:
                problems.append(f"{event.value}: 整个事件段缺失")
                continue
            for ch in required:
                section = body.get(ch)
                subject = str(section.get("subject", "")).strip() if section else ""
                content = str(section.get("content", "")).strip() if section else ""
                if not subject or not content:
                    problems.append(f"{event.value}.{ch}: 段缺失或为空")
        assert problems == [], "系统事件模板缺段:\n" + "\n".join(problems)

    def test_verify_code_email_section(self) -> None:
        """验证码事件仅邮件段，但必须非空。"""
        templates = _load_all_templates()
        for event in _EMAIL_ONLY_EVENTS:
            section = templates.get(event.value, {}).get("email")
            assert section and str(section.get("subject", "")).strip(), f"{event.value} 邮件模板缺失"

    def test_no_duplicate_template_keys_across_files(self) -> None:
        """同一事件键不得在多个模板文件重复定义（防止复制粘贴漂移）。"""
        seen: dict[str, str] = {}
        duplicates = []
        for f in sorted(template_module._TEMPLATE_DIR.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            for key in data:
                if key in seen:
                    duplicates.append(f"{key}: {seen[key]} 与 {f.name}")
                else:
                    seen[key] = f.name
        assert duplicates == [], f"模板事件键跨文件重复: {duplicates}"

    def test_template_keys_are_known_events(self) -> None:
        """模板中的事件键必须是 NotificationEvent 合法 mark（防拼写错误）。"""
        valid = {event.value for event in NotificationEvent}
        unknown = [key for key in _load_all_templates() if key not in valid]
        assert unknown == [], f"模板存在未知事件键: {unknown}"

    def test_every_enum_event_is_classified(self) -> None:
        """每个枚举事件必须归类：个人订阅 / 四段事件 / 免模板 / 仅邮件，防止新事件遗漏。"""
        all_events = {event.value for event in NotificationEvent}
        classified = (
            {e.value for e in PERSONAL_SUBSCRIBABLE_EVENTS}
            | {e.value for e in _FOUR_SECTION_EVENTS}
            | {e.value for e in _NO_TEMPLATE_EVENTS}
            | {e.value for e in _EMAIL_ONLY_EVENTS}
        )
        unaccounted = all_events - classified
        assert unaccounted == set(), f"新枚举事件未归类（补模板并选择归属集合）: {unaccounted}"
