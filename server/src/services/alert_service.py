#!/usr/bin/env python3
"""系统告警服务（管理端 / 开放接口两域共享，位于 services 根目录）。
委托 NotificationDispatcher 发送告警，复用通知系统的：
- 模板渲染
- 多渠道发送
- 发送记录
- 失败重试
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants.constants import MAX_BROADCAST_USER_LIMIT
from src.constants.enums import (
    DEFAULT_ROUTES,
    NotificationChannel,
    NotificationEvent,
    NotificationSource,
    SystemRoleCode,
    UserStatus,
)
from src.core.logger import logger
from src.models.entities.notification_delivery_entity import NotificationDeliveryEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.role_repository import RoleRepository
from src.repositories.system_notification_config_repository import SystemNotificationConfigRepository
from src.repositories.user_repository import UserRepository


def _dedup(items: list[str]) -> list[str]:
    """去重并保持顺序（接收人合并时避免重复推送）。

    Args:
        items: 接收人列表

    Returns:
        list[str]: 去重后的接收人列表
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


class AlertService:
    """统一系统告警服务。
    支持两种发送模式：
    - send(): 指定接收人发送（供外部监控 Webhook 调用），
      自动附加默认推送：超级管理员邮箱 + 超级管理员手机号短信 +
      系统通知渠道配置（system_notification_configs）中已启用的渠道；
    - broadcast(): 广播给全体活跃用户（供健康检查等内部场景调用）
    """

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        session: Session | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._session = session
        self._role_repository: RoleRepository | None = None
        self._user_repository: UserRepository | None = None
        self._system_config_repository: SystemNotificationConfigRepository | None = None

    # ── 默认推送目标 ─────────────────────────────────────

    def _ensure_repositories(self) -> None:
        """惰性构建数据访问组件（复用注入会话，仅只读查询）。"""
        if self._session is None:
            return
        if self._role_repository is None:
            self._role_repository = RoleRepository(session=self._session)
        if self._user_repository is None:
            self._user_repository = UserRepository(session=self._session)
        if self._system_config_repository is None:
            self._system_config_repository = SystemNotificationConfigRepository(session=self._session)

    def _superadmin_contacts(self) -> tuple[list[str], list[str]]:
        """查询全部启用状态超级管理员的邮箱与手机号。

        Returns:
            tuple[list[str], list[str]]: (邮箱列表, 手机号列表)
        """
        self._ensure_repositories()
        if self._role_repository is None or self._user_repository is None:
            return [], []
        role = self._role_repository.get_by_code(SystemRoleCode.SUPERADMIN.mark)
        if role is None:
            return [], []
        emails: list[str] = []
        phones: list[str] = []
        for user in self._user_repository.get_by_role_id(role.id):
            if user.status != UserStatus.ENABLED.value:
                continue
            if user.email:
                emails.append(user.email)
            if user.phone:
                phones.append(user.phone)
        return _dedup(emails), _dedup(phones)

    def _enabled_system_channels(self) -> list[str]:
        """查询系统通知渠道配置（system_notification_configs）中已启用的渠道。

        Returns:
            list[str]: 已启用渠道编码列表（如 ["dingtalk", "feishu"]）
        """
        self._ensure_repositories()
        if self._system_config_repository is None:
            return []
        return [cfg.channel for cfg in self._system_config_repository.list_all() if cfg.enabled]

    # ── 发送 ─────────────────────────────────────────────

    def send(
        self,
        subject: str,
        message: str,
        recipients: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> list[NotificationDeliveryEntity]:
        """发送系统告警到指定接收人，并默认附加推送目标。

        默认推送（在调用方指定接收人之外追加）：
            1. 超级管理员的邮箱（email 渠道）；
            2. 超级管理员的手机号（sms 渠道）；
            3. system_notification_configs 中已启用的系统通知渠道（dingtalk/feishu 等，
               webhook 直发，无需逐个填写接收人）。

        Args:
            subject: 告警标题
            message: 告警内容
            recipients: 渠道→接收人映射，如 {"email": "a@b.com"}
            metadata: 扩展元数据

        Returns:
            list[NotificationDeliveryEntity]: 投递明细列表
        """
        # 1. 规范化调用方指定接收人（值统一为列表）
        merged: dict[str, list[str]] = {
            channel: ([value] if isinstance(value, str) else list(value))
            for channel, value in recipients.items()
        }
        # 2. 发送渠道 = 告警默认路由 ∪ 系统配置渠道（超管短信渠道按需补入）
        channels: list[str] = [c.value for c in DEFAULT_ROUTES[NotificationEvent.SYSTEM_ALERT]]
        if self._session is not None:
            admin_emails, admin_phones = self._superadmin_contacts()
            if admin_emails:
                merged["email"] = _dedup(merged.get("email", []) + admin_emails)
            if admin_phones:
                merged["sms"] = _dedup(merged.get("sms", []) + admin_phones)
                if NotificationChannel.SMS.value not in channels:
                    channels.append(NotificationChannel.SMS.value)
            for sys_channel in self._enabled_system_channels():
                merged.setdefault(sys_channel, [sys_channel])
                if sys_channel not in channels:
                    channels.append(sys_channel)
        variables = {
            "alert_title": subject,
            "alert_message": message,
        }
        return self._dispatcher.dispatch(
            event_type=NotificationEvent.SYSTEM_ALERT,
            recipients=merged,
            variables=variables,
            metadata=metadata,
            source=NotificationSource.ALERT.value,
            channels=channels,
        )

    def broadcast(
        self,
        subject: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """广播系统告警给全体活跃用户。

        Args:
            subject: 告警标题
            message: 告警内容
            metadata: 扩展元数据

        Returns:
            成功发送的用户数
        """
        if self._session is None:
            logger.warning("Alert broadcast skipped: no database session")
            return 0
        repo = UserRepository(session=self._session)
        users, _ = repo.search(status=UserStatus.ENABLED.value, skip=0, limit=MAX_BROADCAST_USER_LIMIT)
        sent_count = 0
        for user in users:
            try:
                self._dispatcher.dispatch_for_user(
                    user_id=user.id,
                    event_type=NotificationEvent.SYSTEM_ALERT,
                    variables={
                        "alert_title": subject,
                        "alert_message": message,
                    },
                    metadata=metadata,
                    source=NotificationSource.ALERT.value,
                )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Alert broadcast failed for user={user.id}: {e}")
        logger.info(
            "Alert broadcast completed: subject=%s users=%d/%d",
            subject,
            sent_count,
            len(users),
        )
        return sent_count
