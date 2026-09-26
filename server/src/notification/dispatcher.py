"""通知调度器 — 事件驱动通知系统的核心。

职责：
    1. 接收业务事件
    2. 根据事件类型查路由表 → 确定要发哪些渠道
    3. 渲染模板
    4. 调用 Provider 发送
    5. 失败写 Redis 重试队列
    6. 全程写 DB 记录

Usage:
    dispatcher = NotificationDispatcher(registry=registry, session=session)

    # 方式一：按用户配置自动发送（推荐）
    dispatcher.dispatch_for_user(
        user_id=1,
        event_type="user.password_changed",
        variables={"username": "张三", "changed_at": "2026-09-24 10:00"},
    )

    # 方式二：手动指定接收人（调试用）
    dispatcher.dispatch(
        event_type="user.password_changed",
        recipients={"email": "a@b.com"},
        variables={"username": "张三", "changed_at": "2026-09-24 10:00"},
    )
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import NotificationChannel, NotificationEvent
from src.core.logger import logger
from src.infras.notification import (
    NotificationMessage,
    NotificationProviderRegistry,
)
from src.models.entities.notification_entity import NotificationRecordEntity
from src.notification.template import render_template
from src.repositories.notification_config_repository import (
    UserNotificationConfigRepository,
)
from src.repositories.notification_repository import NotificationRepository

# 默认路由表：NotificationEvent → [NotificationChannel]
DEFAULT_ROUTES: dict[NotificationEvent, list[NotificationChannel]] = {
    # 用户域
    NotificationEvent.USER_PASSWORD_CHANGED: [NotificationChannel.EMAIL],
    NotificationEvent.USER_PROFILE_UPDATED: [NotificationChannel.EMAIL],
    NotificationEvent.USER_STATUS_CHANGED: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK],
    NotificationEvent.USER_LOGIN_FAILED: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK],
    # 角色权限域
    NotificationEvent.ROLE_ASSIGNED: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK],
    NotificationEvent.PERMISSION_GRANTED: [NotificationChannel.EMAIL],
    NotificationEvent.PERMISSION_REVOKED: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK],
    # 系统域
    NotificationEvent.SYSTEM_ALERT: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK, NotificationChannel.FEISHU],
    NotificationEvent.SYSTEM_MAINTENANCE: [NotificationChannel.EMAIL, NotificationChannel.DINGTALK, NotificationChannel.FEISHU],
}


class NotificationDispatcher:
    """
    通知调度器。
    """

    def __init__(
        self,
        registry: NotificationProviderRegistry,
        session: Session | None = None,
    ) -> None:
        self._registry = registry
        self._session = session
        self._repository = (
            NotificationRepository(session=session) if session else None
        )

    def dispatch(
        self,
        event_type: str | NotificationEvent,
        recipients: dict[str, str],
        variables: dict[str, Any] | None = None,
        channels: list[str | NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[NotificationRecordEntity]:
        """发送通知。

        Args:
            event_type: 事件类型（字符串或枚举），如 "user.password_changed"
            recipients: 渠道→接收人映射，如 {"email": "a@b.com"}
            variables: 模板变量，如 {"username": "张三"}
            channels: 指定通知渠道（覆盖默认路由表），为None 则用路由表
            metadata: 扩展元数据

        Returns:
            通知记录列表
        """
        variables = variables or {}
        # 统一转为枚举，兼容字符串和枚举入参
        event_enum = (
            event_type
            if isinstance(event_type, NotificationEvent)
            else NotificationEvent(str(event_type))
        )
        event_type_str = event_enum.value
        target_channels = channels or DEFAULT_ROUTES.get(event_enum, [NotificationChannel.EMAIL])
        records: list[NotificationRecordEntity] = []

        for channel in target_channels:
            channel_str = channel.value if isinstance(channel, NotificationChannel) else str(channel)
            recipient = recipients.get(channel_str)
            if not recipient:
                logger.debug(
                    "No recipient for channel={} event={}, skipping",
                    channel_str,
                    event_type_str,
                )
                continue

            provider = self._registry.get(channel_str)
            if provider is None:
                logger.warning(
                    "No provider registered for channel={}, skipping", channel_str
                )
                continue

            subject, content = render_template(event_type_str, channel_str, variables)

            # 拼接通知发送记录
            record = NotificationRecordEntity(
                event_type=event_type_str,
                channel=channel_str,
                recipient=recipient,
                subject=subject,
                content=content,
                status="pending",
                metadata_json=json.dumps(metadata, ensure_ascii=False)
                if metadata
                else None,
            )

            # 发送消息
            message = NotificationMessage(
                recipient=recipient,
                subject=subject,
                content=content,
                content_type="html" if channel_str == NotificationChannel.EMAIL.value else "text",
                metadata=metadata or {},
            )
            try:
                success = provider.send(message)
                if success:
                    record.status = "success"
                    record.sent_at = datetime.utcnow()
                else:
                    record.status = "failed"
                    record.error_message = "Provider returned False"
            except Exception as exc:
                record.status = "failed"
                record.error_message = str(exc)[:1000]
                logger.error(
                    "Notification send failed: event={} channel={} error={}",
                    event_type_str,
                    channel_str,
                    exc,
                )

            records.append(record)

        # 持久化通知发送记录
        if self._repository and records:
            self._persist_records(records)

        # 失败的写入重试队列
        failed = [r for r in records if r.status == "failed"]
        if failed:
            self._enqueue_retry(failed)

        return records

    def dispatch_for_user(
        self,
        user_id: int,
        event_type: str | NotificationEvent,
        variables: dict[str, Any] | None = None,
        channels: list[str | NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[NotificationRecordEntity]:
        """根据用户通知配置自动发送通知。

        从 user_notification_configs 表查询用户已启用的渠道配置，
        自动构建 recipients 映射后委托 dispatch() 发送。

        Args:
            user_id: 用户ID
            event_type: 事件类型（字符串或枚举）
            variables: 模板变量
            channels: 指定渠道（覆盖路由表），None 则用路由表
            metadata: 扩展元数据

        Returns:
            通知记录列表
        """
        config_repo = UserNotificationConfigRepository(session=self._session)
        recipients = config_repo.build_recipients_map(user_id)

        if not recipients:
            event_type_str = (
                event_type.value
                if isinstance(event_type, NotificationEvent)
                else str(event_type)
            )
            logger.warning(
                "No notification config found for user_id={}, event={}",
                user_id,
                event_type_str,
            )
            return []

        return self.dispatch(
            event_type=event_type,
            recipients=recipients,
            variables=variables,
            channels=channels,
            metadata=metadata,
        )

    def _persist_records(self, records: list[NotificationRecordEntity]) -> None:
        """持久化通知记录到数据库。"""
        try:
            for record in records:
                self._repository.create(record)
            self._session.commit()  # type: ignore[union-attr]
        except Exception as exc:
            self._session.rollback()  # type: ignore[union-attr]
            logger.error("Failed to persist notification records: {}", exc)

    def _enqueue_retry(self, records: list[NotificationRecordEntity]) -> None:
        """将失败记录写入 Redis 重试队列（ZSET，score 为下次重试时间戳）。"""
        try:
            from src.infras.cache import get_cached_cache_provider

            redis = get_cached_cache_provider()
            for record in records:
                if record.retry_count >= record.max_retries:
                    continue
                retry_data = json.dumps(
                    {
                        "event_type": record.event_type,
                        "channel": record.channel,
                        "recipient": record.recipient,
                        "retry_count": record.retry_count + 1,
                        "metadata": record.metadata_json,
                    },
                    ensure_ascii=False,
                )
                delay = 2**record.retry_count * 60  # 1min, 2min, 4min
                score = time.time() + delay
                redis.zadd("notification:retry_queue", {retry_data: score})
        except Exception as exc:
            logger.error("Failed to enqueue notification retry: {}", exc)
