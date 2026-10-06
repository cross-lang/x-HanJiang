"""系统通知（广播通知）业务逻辑层。
负责系统通知的发布、撤回、重新发布、列表与详情、投递明细查询：
    - 发布：写入 system_notifications 表，并广播站内信（目标受众，产生未读红点）；
      正文可由调用方直接给出，或在 content 为空时按维护参数自动拼接；
    - 幂等：携带 client_request_id 时，同一请求键重复提交直接返回首次发布结果，不重复广播；
    - 定向发布：按 target_type 支持全体用户 / 指定角色 / 指定用户三种受众；
    - 多渠道强推：发布时携带 push_channels，在站内信之外额外按用户渠道配置
      经 Dispatcher 推送（email/dingtalk/feishu），与通知类型解耦；
    - 撤回：标记系统通知为已撤回；
    - 重新发布：已撤回的通知可按首次发布的受众快照重新广播；
    - 投递明细：按通知查询各渠道/状态的投递情况与统计。
数据访问仅经 SystemNotificationRepository / UserRepository / RoleRepository /
StationMessageService / SystemNoticeDeliveryRepository。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.constants.constants import MAX_BROADCAST_USER_LIMIT
from src.constants.enums import (
    NotificationErrorCode,
    NotificationEvent,
    NotificationSource,
    NotificationStatus,
    NotificationTargetType,
    NotificationChannel,
    SystemNotificationStatus,
    SystemNotificationType,
    UserStatus,
)
from src.constants.permissions import PermissionAction
from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger
from src.models.entities.system_notice_delivery_entity import SystemNoticeDeliveryEntity
from src.models.entities.system_notification_entity import SystemNotificationEntity
from src.models.entities.user_entity import UserEntity
from src.notification.dispatcher import NotificationDispatcher
from src.repositories.role_repository import RoleRepository
from src.repositories.system_notice_delivery_repository import SystemNoticeDeliveryRepository
from src.repositories.system_notification_repository import SystemNotificationRepository
from src.repositories.user_repository import UserRepository
from src.schemas.admin.notification import (
    SystemNoticeDeliveryListResponse,
    SystemNotificationResponse,
)
from src.schemas.common import PaginatedResponse
from src.services.admin.station_service import StationMessageService


class SystemNotificationService:
    """系统通知业务逻辑实现。"""

    entity_type: str = "system_notification"  # 审计日志实体类型

    def __init__(
        self,
        notice_repository: SystemNotificationRepository,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        station_service: StationMessageService,
        dispatcher: NotificationDispatcher,
        delivery_repository: SystemNoticeDeliveryRepository,
    ) -> None:
        self._notice_repository = notice_repository
        self._user_repository = user_repository
        self._role_repository = role_repository
        self._station_service = station_service
        self._dispatcher = dispatcher
        self._delivery_repository = delivery_repository

    # ── 发布 ───────────────────────────────────────────────

    def publish(
        self,
        title: str,
        content: str | None,
        notice_type: SystemNotificationType,
        maintenance_time: str | None = None,
        duration_hours: float | None = None,
        reason: str | None = None,
        push_channels: list[str] | None = None,
        client_request_id: str | None = None,
        target_type: NotificationTargetType = NotificationTargetType.ALL,
        target_roles: list[str] | None = None,
        target_user_ids: list[int] | None = None,
        operator: dict[str, Any] | None = None,
    ) -> tuple[SystemNotificationEntity, int, bool]:
        """发布系统通知：写通知记录并广播站内信（目标受众，产生未读红点）。

        正文拼接、定向受众与多渠道强推与通知类型解耦：
        - content 为空且携带维护参数时，正文由维护参数模板自动拼接；
        - target_type 决定受众：all 全员 / roles 指定角色 / users 指定用户；
        - push_channels 非空时，在站内信广播基础上额外按用户渠道配置强推
          （仅 email/dingtalk/feishu，站内信不重复发送）；
        - client_request_id 非空时具备幂等语义：重复提交直接返回首次结果。

        Args:
            title: 通知标题
            content: 通知正文（可为空，携带维护参数时自动拼接）
            notice_type: 通知类型（仅表达语义标签）
            maintenance_time: 维护开始时间（可选）
            duration_hours: 预计持续时长（小时数，可选）
            reason: 维护原因（可选）
            push_channels: 强推渠道列表（可选，不含 station）
            client_request_id: 发布幂等键（可选）
            target_type: 发布受众类型
            target_roles: 目标角色编码列表（target_type=roles 时使用）
            target_user_ids: 目标用户 ID 列表（target_type=users 时使用）
            operator: 操作人上下文（operator_id / operator_name）

        Returns:
            tuple[SystemNotificationEntity, int, bool]:
                (系统通知实体, 多渠道强推成功用户数, 是否幂等命中)

        Raises:
            ValidationException: 目标角色不存在 / 目标用户为空 / 无可用受众时抛出
        """
        # 幂等命中：同一请求键直接返回首次发布结果（不重复广播）
        if client_request_id:
            existing = self._notice_repository.get_by_client_request_id(client_request_id)
            if existing is not None:
                sent_count = int((existing.metadata_json or {}).get("sent_count", 0))
                logger.info(
                    "System notice idempotent hit: id=%s client_request_id=%s", existing.id, client_request_id
                )
                return existing, sent_count, True

        # 录入系统通知记录
        now = datetime.now()
        resolved_content = content or self._build_maintenance_content(
            maintenance_time=maintenance_time,
            duration_hours=duration_hours,
            reason=reason,
        )
        # 维护参数 / 强推渠道 / 受众快照统一存进 metadata_json（不再独立建列）
        metadata: dict[str, Any] = {
            "push_channels": push_channels or [],
            "target_type": target_type.value if isinstance(target_type, NotificationTargetType) else str(target_type),
            "target_roles": target_roles or [],
            "target_user_ids": target_user_ids or [],
        }
        if notice_type == SystemNotificationType.MAINTENANCE:
            metadata["maintenance_time"] = maintenance_time
            metadata["duration_hours"] = duration_hours
            metadata["reason"] = reason
        entity = SystemNotificationEntity(
            title=title,
            content=resolved_content,
            notice_type=notice_type.value if isinstance(notice_type, SystemNotificationType) else str(notice_type),
            status=SystemNotificationStatus.PUBLISHED.value,
            operator_id=operator.get("operator_id") if operator else None,
            operator_name=operator.get("operator_name") if operator else None,
            client_request_id=client_request_id,
            metadata_json=metadata,
            published_at=now,
            created_at=now,
        )
        entity = self._notice_repository.create(entity)
        self._notice_repository.commit()

        # 解析目标受众并广播站内信（默认），记录投递明细
        users = self._resolve_target_users(
            target_type=target_type,
            target_roles=target_roles,
            target_user_ids=target_user_ids,
        )
        user_ids = [u.id for u in users]
        self._station_service.send_station_batch(
            user_ids=user_ids,
            title=title,
            content=resolved_content,
            source=NotificationSource.SYSTEM_NOTICE.value,
            event_type=NotificationEvent.SYSTEM_NOTICE.mark,
            operator_id=operator.get("operator_id") if operator else None,
        )
        self._record_deliveries(
            notification_id=entity.id,
            user_ids=user_ids,
            channel=NotificationChannel.STATION.mark,
            status=NotificationStatus.SUCCESS.value,
            receive_at=now,
        )

        # 若指定了 push_channels 时按目标受众额外强推
        sent_count = 0
        if push_channels:
            sent_count = self._dispatch_push_channels(
                channels=push_channels,
                subject=title,
                content=resolved_content,
                notification_id=entity.id,
                user_ids=user_ids,
                operator=operator,
            )

        # 回写强推成功数快照（供幂等命中与重新发布读取）
        entity.metadata_json = {**metadata, "sent_count": sent_count}
        self._notice_repository.commit()

        # 记录审计日志和系统日志
        self._audit(
            entity_id=entity.id,
            action=PermissionAction.PUBLISH.mark,
            operator=operator,
            after_data={"title": title, "notice_type": entity.notice_type, "status": entity.status},
            remarks=f"发布通知{title}",
        )
        logger.info(
            "System notice published: id=%s type=%s target=%s users=%d push_users=%d operator=%s",
            entity.id,
            entity.notice_type,
            target_type.value if isinstance(target_type, NotificationTargetType) else target_type,
            len(users),
            sent_count,
            entity.operator_name,
        )
        return entity, sent_count, False

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
            raise NotFoundException(
                message="系统通知不存在",
                error_code=NotificationErrorCode.NOTICE_NOT_FOUND.mark,
            )
        if entity.status == SystemNotificationStatus.WITHDRAWN.value:
            return
        entity.status = SystemNotificationStatus.WITHDRAWN.value
        entity.withdrawn_at = datetime.now()
        self._notice_repository.commit()
        self._audit(
            entity_id=notice_id,
            action=PermissionAction.WITHDRAW.mark,
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

    # ── 重新发布 ───────────────────────────────────────────

    def republish(self, notice_id: int, operator: dict[str, Any] | None = None) -> tuple[SystemNotificationEntity, int]:
        """重新发布已撤回的系统通知。

        按首次发布时记录的受众快照（target_type/target_roles/target_user_ids）
        与强推渠道（push_channels）重新广播站内信与强推渠道，
        已送达的站内信不删除（重新发布以新消息产生新红点）。

        Args:
            notice_id: 系统通知 ID
            operator: 操作人上下文

        Returns:
            tuple[SystemNotificationEntity, int]: (通知实体, 强推成功用户数)

        Raises:
            NotFoundException: 系统通知不存在时抛出
            ValidationException: 当前状态不是已撤回时抛出
        """
        entity = self._notice_repository.get_by_id(notice_id)
        if entity is None:
            raise NotFoundException(
                message="系统通知不存在",
                error_code=NotificationErrorCode.NOTICE_NOT_FOUND.mark,
            )
        if entity.status != SystemNotificationStatus.WITHDRAWN.value:
            raise ValidationException(
                message="仅已撤回的通知可重新发布",
                error_code=NotificationErrorCode.NOTICE_CANNOT_REPUBLISH.mark,
            )

        metadata = entity.metadata_json or {}
        target_type = NotificationTargetType(metadata.get("target_type", NotificationTargetType.ALL.value))
        push_channels = metadata.get("push_channels") or []
        now = datetime.now()

        users = self._resolve_target_users(
            target_type=target_type,
            target_roles=metadata.get("target_roles"),
            target_user_ids=metadata.get("target_user_ids"),
        )
        user_ids = [u.id for u in users]
        self._station_service.send_station_batch(
            user_ids=user_ids,
            title=entity.title,
            content=entity.content,
            source=NotificationSource.SYSTEM_NOTICE.value,
            event_type=NotificationEvent.SYSTEM_NOTICE.mark,
            operator_id=operator.get("operator_id") if operator else None,
        )
        self._record_deliveries(
            notification_id=entity.id,
            user_ids=user_ids,
            channel="station",
            status=NotificationStatus.SUCCESS.value,
            receive_at=now,
        )

        sent_count = 0
        if push_channels:
            sent_count = self._dispatch_push_channels(
                channels=push_channels,
                subject=entity.title,
                content=entity.content,
                notification_id=entity.id,
                user_ids=user_ids,
                operator=operator,
            )

        entity.status = SystemNotificationStatus.PUBLISHED.value
        entity.withdrawn_at = None
        entity.published_at = now
        entity.metadata_json = {**metadata, "sent_count": sent_count}
        self._notice_repository.commit()

        self._audit(
            entity_id=notice_id,
            action=PermissionAction.REPUBLISH.mark,
            operator=operator,
            before_data={"status": SystemNotificationStatus.WITHDRAWN.value},
            after_data={"status": SystemNotificationStatus.PUBLISHED.value},
            remarks=f"重新发布通知{entity.title}",
        )
        logger.info(
            "System notice republished: id=%s users=%d push_users=%d operator=%s",
            notice_id,
            len(users),
            sent_count,
            operator.get("operator_name") if operator else None,
        )
        return entity, sent_count

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
            raise NotFoundException(
                message="系统通知不存在",
                error_code=NotificationErrorCode.NOTICE_NOT_FOUND.mark,
            )
        return SystemNotificationResponse.model_validate(entity)

    def get_deliveries(
        self,
        notice_id: int,
        channel: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SystemNoticeDeliveryListResponse:
        """查询系统通知投递明细（分页 + 状态统计）。

        Args:
            notice_id: 系统通知 ID
            channel: 渠道过滤（可选）
            status: 投递状态过滤（可选）
            page: 页码
            page_size: 每页数量

        Returns:
            SystemNoticeDeliveryListResponse: 投递明细分页与状态统计

        Raises:
            NotFoundException: 系统通知不存在时抛出
        """
        if self._notice_repository.get_by_id(notice_id) is None:
            raise NotFoundException(
                message="系统通知不存在",
                error_code=NotificationErrorCode.NOTICE_NOT_FOUND.mark,
            )
        skip = (page - 1) * page_size
        items, total = self._delivery_repository.list_by_notification(
            notification_id=notice_id,
            channel=channel,
            status=status,
            skip=skip,
            limit=page_size,
        )
        stats = self._delivery_repository.count_by_notification_status(notice_id)
        return SystemNoticeDeliveryListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
            stats=stats,
        )

    # ── 受众解析与推送 ─────────────────────────────────────

    def _resolve_target_users(
        self,
        target_type: NotificationTargetType,
        target_roles: list[str] | None = None,
        target_user_ids: list[int] | None = None,
    ) -> list[UserEntity]:
        """解析发布受众用户列表（去重，仅未删除用户）。

        Args:
            target_type: 受众类型（all/roles/users）
            target_roles: 目标角色编码列表
            target_user_ids: 目标用户 ID 列表

        Returns:
            list[UserEntity]: 目标用户实体列表（去重）

        Raises:
            ValidationException: 目标角色不存在 / 目标用户为空 / 无可用受众时抛出
        """
        if target_type == NotificationTargetType.ROLES:
            user_set: dict[int, UserEntity] = {}
            for role_code in target_roles or []:
                role = self._role_repository.get_by_code(role_code)
                if role is None:
                    raise ValidationException(
                        message=f"目标角色不存在：{role_code}",
                        error_code=NotificationErrorCode.TARGET_ROLES_NOT_FOUND.mark,
                    )
                for user in self._user_repository.get_by_role_id(role.id):
                    user_set[user.id] = user
            users = list(user_set.values())
            if not users:
                raise ValidationException(
                    message="目标角色下没有可用用户",
                    error_code=NotificationErrorCode.TARGET_USERS_EMPTY.mark,
                )
            return users

        if target_type == NotificationTargetType.USERS:
            users = self._user_repository.get_by_ids(target_user_ids or [])
            if not users:
                raise ValidationException(
                    message="目标用户不存在或已删除",
                    error_code=NotificationErrorCode.TARGET_USERS_EMPTY.mark,
                )
            return users

        # 默认：全体活跃用户（与既有广播语义保持一致）
        users, _ = self._user_repository.search(
            status=UserStatus.ENABLED.value,
            skip=0,
            limit=MAX_BROADCAST_USER_LIMIT,
        )
        if not users:
            raise ValidationException(
                message="没有可推送的活跃用户",
                error_code=NotificationErrorCode.NO_ACTIVE_USERS.mark,
            )
        return users

    def _dispatch_push_channels(
        self,
        channels: list[str],
        subject: str,
        content: str,
        notification_id: int,
        user_ids: list[int],
        operator: dict[str, Any] | None = None,
    ) -> int:
        """按用户渠道配置向强推渠道推送已渲染好的正文（不重复写站内信）。

        显式指定渠道覆盖 DEFAULT_ROUTES，且使用 pre_rendered 直发内容，
        不依赖 YAML 模板文件；单用户失败不影响整体广播。

        Args:
            channels: 强推渠道列表（email/dingtalk/feishu）
            subject: 已渲染好的通知主题
            content: 已渲染好的通知正文
            notification_id: 系统通知 ID（投递明细关联）
            user_ids: 目标用户 ID 列表
            operator: 操作人上下文

        Returns:
            int: 成功推送的用户数
        """
        sent_count = 0
        for user_id in user_ids:
            try:
                self._dispatcher.dispatch_for_user(
                    user_id=user_id,
                    event_type=NotificationEvent.SYSTEM_NOTICE,
                    channels=channels,
                    pre_rendered=(subject, content),
                    metadata={"operator": operator.get("operator_name") if operator else None},
                    source=NotificationSource.SYSTEM_NOTICE.value,
                    system_notification_id=notification_id,
                )
                sent_count += 1
            except Exception as exc:  # noqa: BLE001 - 单用户失败不影响整体广播
                logger.warning("Push channel dispatch failed for user=%s: %s", user_id, exc)
        return sent_count

    @staticmethod
    def _build_maintenance_content(
        maintenance_time: str | None,
        duration_hours: float | None,
        reason: str | None = None,
    ) -> str:
        """按维护参数模板拼接正文（可选的维护参数模板，与通知类型解耦）。

        Args:
            maintenance_time: 维护开始时间
            duration_hours: 预计持续时长（小时数）
            reason: 维护原因（可选）

        Returns:
            str: 拼接后的维护通知正文
        """
        content = f"系统将于 {maintenance_time} 进行维护，预计持续 {duration_hours} 小时。"
        if reason:
            content += f" 维护原因：{reason}"
        return content

    def _record_deliveries(
        self,
        notification_id: int,
        user_ids: list[int],
        channel: str,
        status: str,
        receive_at: datetime,
    ) -> None:
        """批量记录站内信渠道的投递明细（单事务一次提交）。

        Args:
            notification_id: 系统通知 ID
            user_ids: 目标用户 ID 列表
            channel: 发送渠道
            status: 投递状态
            receive_at: 送达时间
        """
        deliveries = [
            SystemNoticeDeliveryEntity(
                system_notification_id=notification_id,
                source=NotificationSource.SYSTEM_NOTICE.value,
                event_type=NotificationEvent.SYSTEM_NOTICE.mark,
                user_id=user_id,
                channel=channel,
                recipient=f"user:{user_id}",
                status=status,
                receive_at=receive_at,
            )
            for user_id in user_ids
        ]
        self._delivery_repository.create_batch(deliveries)
        self._delivery_repository.commit()

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
            action: 操作类型（publish / withdraw / republish 等）
            operator: 操作人上下文（operator_id / operator_name / ip_address）
            before_data: 变更前数据快照
            after_data: 变更后数据快照
            remarks: 备注说明
        """
        try:
            from src.services.admin.audit_service import AuditService

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
