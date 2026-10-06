"""通知调度器 — 事件驱动通知系统的核心。

职责：

    1. 接收业务事件
    2. 根据事件类型查路由表 → 确定要发哪些渠道
    3. 渲染模板
    4. 调用 Provider 发送
    5. 失败写 Redis 重试队列
    6. 全程写投递明细（notifications_delivery）与站内信（station_messages）

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
import re
import time
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import (
    DEFAULT_ROUTES,
    NotificationChannel,
    NotificationEvent,
    NotificationSource,
    NotificationStatus,
)
from src.core.logger import logger
from src.infras.notification import (
    NotificationMessage,
    NotificationProviderRegistry,
)
from src.models.entities.notification_delivery_entity import NotificationDeliveryEntity
from src.models.entities.station_message_entity import StationMessageEntity
from src.notification.template import render_template
from src.repositories.notification_config_repository import (
    UserNotificationConfigRepository,
)
from src.repositories.notification_delivery_repository import NotificationDeliveryRepository

_STATION_RECIPIENT_RE = re.compile(r"^user:(\d+)$")


def _resolve_event(event_type: str) -> NotificationEvent:
    """按 mark 反查通知事件枚举成员；未命中抛出 ValueError（保持枚举构造语义）。"""
    for member in NotificationEvent:
        if member.mark == event_type:
            return member
    raise ValueError(f"未知通知事件: {event_type}")


class NotificationDispatcher:
    """通知调度器。

    面向抽象渠道 Provider 发送，并将每次投递的实际情况写入
    notifications_delivery（外部渠道）/ station_messages（站内信）。
    """

    def __init__(
        self,
        registry: NotificationProviderRegistry,
        session: Session | None = None,
    ) -> None:
        """初始化调度器。

        Args:
            registry: 渠道 Provider 注册表
            session: SQLAlchemy 会话（可选，未提供则投递明细不落库）
        """
        self._registry = registry
        self._session = session
        self._repository = NotificationDeliveryRepository(session=session) if session else None

    def dispatch(
        self,
        event_type: str | NotificationEvent,
        recipients: Mapping[str, str | list[str]],
        variables: dict[str, Any] | None = None,
        channels: list[str | NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
        pre_rendered: tuple[str, str] | None = None,
        *,
        source: str = NotificationSource.MANUAL.value,
        system_notification_id: int | None = None,
    ) -> list[NotificationDeliveryEntity]:
        """发送通知并记录投递明细。

        同一渠道支持多个接收人（值可为单个字符串或字符串列表），
        每个接收人独立生成一条投递明细并发送一次；
        站内信渠道（station）额外写入 station_messages 收件箱。

        Args:
            event_type: 事件类型（字符串或枚举），如 "user.password_changed"
            recipients: 渠道→接收人映射，如 {"email": ["a@b.com", "c@d.com"]}
            variables: 模板变量，如 {"username": "张三"}
            channels: 指定通知渠道（覆盖默认路由表），为 None 则用路由表
            metadata: 扩展元数据
            pre_rendered: 已渲染好的 (subject, content)，提供后跳过模板渲染，
                适用于正文由调用方直接给出的事件（如系统通知广播），避免依赖模板文件
            source: 通知来源（system_notice/station/alert/openapi_app）
            system_notification_id: 关联系统通知 ID（系统通知广播时传入）

        Returns:
            list[NotificationDeliveryEntity]: 投递明细列表
        """
        variables = variables or {}
        # 统一转为枚举，兼容字符串和枚举入参
        event_enum = event_type if isinstance(event_type, NotificationEvent) else _resolve_event(str(event_type))
        event_type_str = event_enum.value
        target_channels = channels or DEFAULT_ROUTES.get(event_enum, [NotificationChannel.EMAIL])
        deliveries: list[NotificationDeliveryEntity] = []
        inbox_items: list[tuple[NotificationDeliveryEntity, str, str]] = []
        retry_items: list[tuple[NotificationDeliveryEntity, str, str]] = []
        for channel in target_channels:
            channel_str = channel.value if isinstance(channel, NotificationChannel) else str(channel)
            recipient_spec = recipients.get(channel_str)
            if not recipient_spec:
                logger.debug(
                    "No recipient for channel={} event={}, skipping",
                    channel_str,
                    event_type_str,
                )
                continue
            recipient_list = recipient_spec if isinstance(recipient_spec, list) else [recipient_spec]
            provider = self._registry.get(channel_str)
            if provider is None:
                logger.warning("No provider registered for channel={}, skipping", channel_str)
                continue
            if pre_rendered is not None:
                subject, content = pre_rendered
            else:
                subject, content = render_template(event_type_str, channel_str, variables)
            for recipient in recipient_list:
                if not recipient:
                    continue
                delivery = NotificationDeliveryEntity(
                    system_notification_id=system_notification_id,
                    source=source,
                    event_type=event_type_str,
                    channel=channel_str,
                    recipient=recipient,
                    status=NotificationStatus.PENDING.value,
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
                        delivery.status = NotificationStatus.SUCCESS.value
                        delivery.receive_at = datetime.now()
                    else:
                        delivery.status = NotificationStatus.FAILED.value
                        delivery.error_message = "Provider returned False"
                except Exception as exc:
                    delivery.status = NotificationStatus.FAILED.value
                    delivery.error_message = str(exc)[:1000]
                    logger.error(
                        "Notification send failed: event={} channel={} error={}",
                        event_type_str,
                        channel_str,
                        exc,
                    )
                deliveries.append(delivery)
                if channel_str == NotificationChannel.STATION.value:
                    inbox_items.append((delivery, subject, content))
                elif delivery.status == NotificationStatus.FAILED.value:
                    retry_items.append((delivery, subject, content))
        # 持久化投递明细（站内信渠道额外写收件箱）
        if self._repository and deliveries:
            self._persist_deliveries(deliveries)
        if self._session is not None and inbox_items:
            self._write_station_inboxes(source, inbox_items)
        # 失败的写入重试队列
        if retry_items:
            self._enqueue_retry(retry_items)
        return deliveries

    def dispatch_for_user(
        self,
        user_id: int,
        event_type: str | NotificationEvent,
        variables: dict[str, Any] | None = None,
        channels: list[str | NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
        pre_rendered: tuple[str, str] | None = None,
        *,
        source: str = NotificationSource.MANUAL.value,
        system_notification_id: int | None = None,
    ) -> list[NotificationDeliveryEntity]:
        """根据用户通知配置自动发送通知。

        从 user_notification_configs 表查询用户已启用的渠道配置，
        自动构建 recipients 映射后委托 dispatch() 发送。

        Args:
            user_id: 用户 ID
            event_type: 事件类型（字符串或枚举）
            variables: 模板变量
            channels: 指定渠道（覆盖路由表），None 则用路由表
            metadata: 扩展元数据
            pre_rendered: 已渲染好的 (subject, content)，提供后跳过模板渲染
            source: 通知来源（system_notice/station/alert/openapi_app）
            system_notification_id: 关联系统通知 ID

        Returns:
            list[NotificationDeliveryEntity]: 投递明细列表
        """
        config_repo = UserNotificationConfigRepository(session=self._session)
        event_type_str = event_type.value if isinstance(event_type, NotificationEvent) else str(event_type)
        recipients = config_repo.build_recipients_map(user_id, event_type_str)
        if not recipients:
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
            pre_rendered=pre_rendered,
            source=source,
            system_notification_id=system_notification_id,
        )

    def dispatch_pre_rendered(
        self,
        event_type: str | NotificationEvent,
        recipients: dict[str, str | list[str]],
        subject: str,
        content: str,
        channels: list[str | NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        source: str = NotificationSource.MANUAL.value,
        system_notification_id: int | None = None,
    ) -> list[NotificationDeliveryEntity]:
        """用已渲染好的主题与正文发送通知（跳过模板渲染）。

        适用于正文由调用方直接给出的场景（如系统通知广播/告警），
        复用 dispatch() 的投递明细与失败重试能力，不依赖 YAML 模板文件。

        Args:
            event_type: 事件类型（字符串或枚举）
            recipients: 渠道→接收人映射（单个字符串或字符串列表）
            subject: 已渲染好的通知主题
            content: 已渲染好的通知正文
            channels: 指定通知渠道（覆盖路由表），None 则用路由表
            metadata: 扩展元数据
            source: 通知来源
            system_notification_id: 关联系统通知 ID

        Returns:
            list[NotificationDeliveryEntity]: 投递明细列表
        """
        return self.dispatch(
            event_type=event_type,
            recipients=recipients,
            variables={},
            channels=channels,
            metadata=metadata,
            pre_rendered=(subject, content),
            source=source,
            system_notification_id=system_notification_id,
        )

    def _persist_deliveries(self, deliveries: list[NotificationDeliveryEntity]) -> None:
        """持久化投递明细到数据库。"""
        if self._repository is None or self._session is None:
            return
        try:
            for delivery in deliveries:
                self._repository.create(delivery)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            logger.error("Failed to persist notification deliveries: {}", exc)

    def _write_station_inboxes(
        self,
        source: str,
        inbox_items: list[tuple[NotificationDeliveryEntity, str, str]],
    ) -> None:
        """将站内信渠道的投递同步写入 station_messages 收件箱。

        Args:
            source: 通知来源
            inbox_items: (投递明细, 主题, 正文) 三元组列表
        """
        if self._session is None:
            return
        messages: list[StationMessageEntity] = []
        for delivery, subject, content in inbox_items:
            match = _STATION_RECIPIENT_RE.match(delivery.recipient)
            if match is None:
                continue
            messages.append(
                StationMessageEntity(
                    user_id=int(match.group(1)),
                    subject=subject,
                    content=content,
                    source=source,
                    event_type=delivery.event_type,
                    is_read=False,
                )
            )
        if messages:
            self._session.add_all(messages)
            try:
                self._session.commit()
            except Exception as exc:
                self._session.rollback()
                logger.error("Failed to persist station inbox messages: {}", exc)

    def _enqueue_retry(self, retry_items: list[tuple[NotificationDeliveryEntity, str, str]]) -> None:
        """将失败投递写入 Redis 重试队列（ZSET，score 为下次重试时间戳）。

        载荷携带投递 ID 与渲染后正文，重试成功后直接回写状态，
        修复此前重试队列不含正文、无法真正重发的问题。

        Args:
            retry_items: (投递明细, 主题, 正文) 三元组列表
        """
        from src.notification.bootstrap import NOTIFICATION_RETRY_QUEUE_KEY

        try:
            from src.infras.cache import get_cached_cache_provider

            redis = get_cached_cache_provider()
            for delivery, subject, content in retry_items:
                if delivery.retry_count >= delivery.max_retries:
                    continue
                retry_data = json.dumps(
                    {
                        "delivery_id": delivery.id,
                        "channel": delivery.channel,
                        "recipient": delivery.recipient,
                        "subject": subject,
                        "content": content,
                        "retry_count": delivery.retry_count + 1,
                    },
                    ensure_ascii=False,
                )
                delay = 2**delivery.retry_count * 60  # 1min, 2min, 4min
                score = time.time() + delay
                redis.zadd(NOTIFICATION_RETRY_QUEUE_KEY, {retry_data: score})
        except Exception as exc:
            logger.error("Failed to enqueue notification retry: {}", exc)
