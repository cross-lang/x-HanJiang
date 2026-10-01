"""系统通知（广播通知）业务逻辑层。
负责系统通知的发布、撤回、列表与详情：
    - 发布：写入 system_notifications 表，并广播站内信（全体活跃用户，产生未读红点）；
    - 维护通知：在站内信广播基础上，额外按用户渠道配置经 Dispatcher 推送多渠道；
    - 撤回：标记系统通知为已撤回。
数据访问仅经 SystemNotificationRepository / UserRepository / StationMessageService。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.constants.constants import MAX_BROADCAST_USER_LIMIT
from src.constants.enums import (
    NotificationEvent,
    SystemNotificationStatus,
    SystemNotificationType,
    UserStatus,
)
from src.core.exceptions import NotFoundException
from src.core.logger import logger
from src.models.entities.system_notification_entity import SystemNotificationEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.system_notification_repository import SystemNotificationRepository
from src.repositories.user_repository import UserRepository
from src.schemas.common import PaginatedResponse
from src.schemas.notification import SystemNotificationResponse
from src.services.station_service import StationMessageService


class SystemNotificationService:
    """系统通知业务逻辑实现。"""

    entity_type: str = "system_notification"  # 审计日志实体类型

    def __init__(
        self,
        notice_repository: SystemNotificationRepository,
        user_repository: UserRepository,
        station_service: StationMessageService,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._notice_repository = notice_repository
        self._user_repository = user_repository
        self._station_service = station_service
        self._dispatcher = dispatcher

    # ── 发布 ───────────────────────────────────────────────

    def publish(
        self,
        title: str,
        content: str,
        notice_type: SystemNotificationType,
        maintenance_time: str | None = None,
        duration: str | None = None,
        reason: str | None = None,
        operator: dict[str, Any] | None = None,
    ) -> SystemNotificationEntity:
        """发布系统通知：写通知记录并广播站内信（全体活跃用户，产生未读红点）。

        Args:
            title: 通知标题
            content: 通知正文
            notice_type: 通知类型
            maintenance_time: 维护开始时间（maintenance 类型）
            duration: 预计持续时长（maintenance 类型）
            reason: 维护原因（可选）
            operator: 操作人上下文（operator_id / operator_name）

        Returns:
            SystemNotificationEntity: 已发布的系统通知实体

        Raises:
            NotFoundException: 无活跃用户可推送时抛出
        """
        now = datetime.now()
        entity = SystemNotificationEntity(
            title=title,
            content=content,
            notice_type=notice_type.value if isinstance(notice_type, SystemNotificationType) else str(notice_type),
            maintenance_time=maintenance_time,
            duration=duration,
            reason=reason,
            status=SystemNotificationStatus.PUBLISHED.value,
            operator_id=operator.get("operator_id") if operator else None,
            operator_name=operator.get("operator_name") if operator else None,
            published_at=now,
            created_at=now,
        )
        entity = self._notice_repository.create(entity)
        self._notice_repository.commit()

        users, _ = self._user_repository.search(
            status=UserStatus.ENABLED.value,
            skip=0,
            limit=MAX_BROADCAST_USER_LIMIT,
        )
        if not users:
            raise NotFoundException(message="没有可推送的活跃用户")

        self._station_service.send_station_batch(
            user_ids=[u.id for u in users],
            title=title,
            content=content,
            event_type=NotificationEvent.SYSTEM_NOTICE.mark,
        )
        self._audit(
            entity_id=entity.id,
            action="publish",
            operator=operator,
            after_data={"title": title, "notice_type": entity.notice_type, "status": entity.status},
            remarks=f"发布通知{title}",
        )
        logger.info(
            "System notice published: id=%s type=%s users=%d operator=%s",
            entity.id,
            entity.notice_type,
            len(users),
            entity.operator_name,
        )
        return entity

    def publish_maintenance(
        self,
        title: str,
        maintenance_time: str,
        duration: str,
        reason: str | None = None,
        operator: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        """发布系统维护通知：站内信广播 + 按用户渠道配置推送多渠道。

        站内信标题使用发布者填写的内容；
        正文由系统按维护时间/时长/原因自动拼接；
        维护参数同时作为变量传递给多渠道通知模板。

        Args:
            title: 通知标题（发布者填写）
            maintenance_time: 维护开始时间
            duration: 预计持续时长（需包含单位）
            reason: 维护原因（可选）
            operator: 操作人上下文

        Returns:
            tuple[int, int]: (系统通知 ID, 多渠道推送成功用户数)
        """
        content = f"系统将于 {maintenance_time} 进行维护，预计持续 {duration}。"
        if reason:
            content += f" 维护原因：{reason}"
        entity = self.publish(
            title=title,
            content=content,
            notice_type=SystemNotificationType.MAINTENANCE,
            maintenance_time=maintenance_time,
            duration=duration,
            reason=reason,
            operator=operator,
        )
        variables: dict[str, Any] = {"maintenance_time": maintenance_time, "duration": duration}
        if reason:
            variables["reason"] = reason
        sent_count = self._dispatch_maintenance_channels(variables, operator)
        return entity.id, sent_count

    def _dispatch_maintenance_channels(
        self,
        variables: dict[str, Any],
        operator: dict[str, Any] | None = None,
    ) -> int:
        """按用户渠道配置广播 SYSTEM_MAINTENANCE 事件（email/dingtalk/feishu 等）。"""
        users, _ = self._user_repository.search(
            status=UserStatus.ENABLED.value,
            skip=0,
            limit=MAX_BROADCAST_USER_LIMIT,
        )
        sent_count = 0
        for user in users:
            try:
                self._dispatcher.dispatch_for_user(
                    user_id=user.id,
                    event_type=NotificationEvent.SYSTEM_MAINTENANCE,
                    variables=variables,
                    metadata={"operator": operator.get("operator_name") if operator else None},
                )
                sent_count += 1
            except Exception as exc:  # noqa: BLE001 - 单用户失败不影响整体广播
                logger.warning("Maintenance channel dispatch failed for user=%s: %s", user.id, exc)
        return sent_count

    # ── 撤回 ───────────────────────────────────────────────

    def withdraw(self, notice_id: int, operator: dict[str, Any] | None = None) -> None:
        """撤回已发布的系统通知（幂等，已撤回则直接返回）。

        Args:
            notice_id: 系统通知 ID
            operator: 操作人上下文

        Raises:
            NotFoundException: 系统通知不存在时抛出
        """
        entity = self._notice_repository.get_by_id(notice_id)
        if entity is None:
            raise NotFoundException(message="系统通知不存在")
        if entity.status == SystemNotificationStatus.WITHDRAWN.value:
            return
        entity.status = SystemNotificationStatus.WITHDRAWN.value
        entity.withdrawn_at = datetime.now()
        self._notice_repository.commit()
        self._audit(
            entity_id=notice_id,
            action="withdraw",
            operator=operator,
            before_data={"status": SystemNotificationStatus.PUBLISHED.value},
            after_data={"status": SystemNotificationStatus.WITHDRAWN.value},
            remarks=f"撤回通知{entity.title}",
        )
        logger.info(
            "System notice withdrawn: id=%s operator=%s",
            notice_id,
            operator.get("operator_name") if operator else None,
        )

    # ── 查询 ───────────────────────────────────────────────

    def list_notices(
        self,
        page: int = 1,
        page_size: int = 20,
        notice_type: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> PaginatedResponse[SystemNotificationResponse]:
        """分页查询系统通知（按发布时间倒序）。

        Args:
            page: 页码
            page_size: 每页数量
            notice_type: 通知类型过滤
            status: 发布状态过滤
            keyword: 标题/正文关键字搜索

        Returns:
            PaginatedResponse[SystemNotificationResponse]: 分页结果
        """
        skip = (page - 1) * page_size
        items, total = self._notice_repository.search(
            notice_type=notice_type,
            status=status,
            keyword=keyword,
            skip=skip,
            limit=page_size,
        )
        return PaginatedResponse[SystemNotificationResponse](
            items=[SystemNotificationResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
        )

    def get_notice(self, notice_id: int) -> SystemNotificationResponse:
        """查询系统通知详情。

        Args:
            notice_id: 系统通知 ID

        Returns:
            SystemNotificationResponse: 系统通知详情

        Raises:
            NotFoundException: 系统通知不存在时抛出
        """
        entity = self._notice_repository.get_by_id(notice_id)
        if entity is None:
            raise NotFoundException(message="系统通知不存在")
        return SystemNotificationResponse.model_validate(entity)

    def _audit(
        self,
        entity_id: Any,
        action: str,
        operator: dict[str, Any] | None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        remarks: str | None = None,
    ) -> None:
        """记录审计日志（失败不影响主流程）。

        Args:
            entity_id: 实体主键
            action: 操作类型（publish / withdraw 等）
            operator: 操作人上下文（operator_id / ip_address）
            before_data: 变更前数据快照
            after_data: 变更后数据快照
            remarks: 备注说明
        """
        try:
            from src.services.audit_service import AuditService

            AuditService().log_event(
                entity_type=self.entity_type,
                entity_id=entity_id,
                action=action,
                operator_id=operator.get("operator_id") if operator else None,
                before_data=before_data,
                after_data=after_data,
                ip_address=operator.get("ip_address") if operator else None,
                remarks=remarks or f"{self.entity_type} {action}",
            )
        except Exception as exc:  # noqa: BLE001 - 审计失败不阻断主流程
            logger.warning("审计日志写入失败 entity_type=%s action=%s: %s", self.entity_type, action, exc)
