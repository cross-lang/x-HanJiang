"""系统通知投递明细数据访问层。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.entities.notification_delivery_entity import NotificationDeliveryEntity
from src.repositories.base_repository import BaseRepository


class NotificationDeliveryRepository(BaseRepository[NotificationDeliveryEntity, int]):
    """系统通知投递明细 Repository。

    负责投递明细的写入、分页查询、状态统计与失败重试队列读取。
    重试状态机：pending → success / failed；failed 且 retry_count < max_retries
    时由调度任务取出重发，成功后回写状态。
    """

    model_class = NotificationDeliveryEntity

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def create_batch(self, deliveries: list[NotificationDeliveryEntity]) -> None:
        """批量写入投递明细（单事务一次提交）。

        Args:
            deliveries: 投递明细实体列表
        """
        for delivery in deliveries:
            self.session.add(delivery)
        self.session.flush()

    def list_by_notification(
        self,
        notification_id: int,
        channel: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[NotificationDeliveryEntity], int]:
        """按系统通知分页查询投递明细（按创建时间倒序，可按渠道/状态过滤）。

        Args:
            notification_id: 系统通知 ID
            channel: 渠道过滤（可选）
            status: 投递状态过滤（可选）
            skip: 偏移量
            limit: 每页数量

        Returns:
            tuple[list[NotificationDeliveryEntity], int]: (投递明细列表, 总数)
        """
        conditions: list[Any] = [self.model_class.system_notification_id == notification_id]
        if channel:
            conditions.append(self.model_class.channel == channel)
        if status:
            conditions.append(self.model_class.status == status)
        return self._paginate(conditions=conditions, skip=skip, limit=limit)

    def count_by_notification_status(self, notification_id: int) -> dict[str, int]:
        """按投递状态统计某系统通知的投递数量（pending/success/failed 等）。

        Args:
            notification_id: 系统通知 ID

        Returns:
            dict[str, int]: 状态 → 数量映射
        """
        stmt = (
            select(self.model_class.status, func.count())
            .where(self.model_class.system_notification_id == notification_id)
            .group_by(self.model_class.status)
        )
        rows = self.session.execute(stmt).all()
        return {str(r[0]): int(r[1]) for r in rows}

    def search_records(
        self,
        event_type: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        source: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[NotificationDeliveryEntity], int]:
        """按事件类型/渠道/状态/来源分页查询投递明细（按时间倒序）。

        Args:
            event_type: 事件类型过滤
            channel: 渠道过滤
            status: 状态过滤
            source: 来源过滤
            skip: 偏移量
            limit: 每页数量

        Returns:
            tuple[list[NotificationDeliveryEntity], int]: (投递明细列表, 总数)
        """
        conditions: list[Any] = []
        if event_type:
            conditions.append(self.model_class.event_type == event_type)
        if channel:
            conditions.append(self.model_class.channel == channel)
        if status:
            conditions.append(self.model_class.status == status)
        if source:
            conditions.append(self.model_class.source == source)
        return self._paginate(conditions=conditions, skip=skip, limit=limit)

    def get_pending_retry(self, limit: int = 50) -> list[NotificationDeliveryEntity]:
        """查询待重试的失败投递明细。

        Args:
            limit: 最大返回条数

        Returns:
            list[NotificationDeliveryEntity]: 待重试投递明细列表
        """
        stmt = (
            self._base_query()
            .where(
                self.model_class.status == "failed",
                self.model_class.retry_count < self.model_class.max_retries,
            )
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_by_status(self, status: str) -> int:
        """按状态统计投递数量。

        Args:
            status: 状态（pending/success/failed）

        Returns:
            int: 数量
        """
        stmt = select(func.count()).where(self.model_class.status == status)
        return self.session.execute(stmt).scalar() or 0

    def mark_retry_failed(self, delivery: NotificationDeliveryEntity, error_message: str) -> None:
        """重试失败：重试次数 +1 并记录错误信息。

        Args:
            delivery: 投递明细实体
            error_message: 错误信息
        """
        delivery.retry_count += 1
        delivery.error_message = error_message[:1000]
        delivery.updated_at = datetime.now()
        self.session.flush()

    def mark_sent(self, delivery: NotificationDeliveryEntity) -> None:
        """标记投递成功（送达时间）。

        Args:
            delivery: 投递明细实体
        """
        delivery.status = "success"
        delivery.receive_at = datetime.now()
        delivery.updated_at = datetime.now()
        self.session.flush()

    @staticmethod
    def _entity_name() -> str:
        return "通知投递明细"
