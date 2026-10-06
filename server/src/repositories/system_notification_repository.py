"""系统通知仓库。
仅负责 system_notifications 表的 CRUD 与分页查询，不含业务判断。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.entities.system_notification_entity import SystemNotificationEntity


class SystemNotificationRepository:
    """系统通知数据访问层。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, entity: SystemNotificationEntity) -> SystemNotificationEntity:
        """新增系统通知。

        Args:
            entity: 系统通知实体

        Returns:
            SystemNotificationEntity: 带主键的持久化实体
        """
        self._session.add(entity)
        self._session.flush()
        return entity

    def get_by_id(self, notice_id: int) -> SystemNotificationEntity | None:
        """按主键查询系统通知。

        Args:
            notice_id: 系统通知 ID

        Returns:
            SystemNotificationEntity | None: 通知实体或不存在时为 None
        """
        return (
            self._session.execute(select(SystemNotificationEntity).where(SystemNotificationEntity.id == notice_id))
            .scalars()
            .first()
        )

    def get_by_client_request_id(self, client_request_id: str) -> SystemNotificationEntity | None:
        """按发布幂等键查询已存在的系统通知（幂等命中检测）。

        Args:
            client_request_id: 发布幂等键

        Returns:
            SystemNotificationEntity | None: 已存在的通知实体或未命中时为 None
        """
        return (
            self._session.execute(
                select(SystemNotificationEntity).where(
                    SystemNotificationEntity.client_request_id == client_request_id
                )
            )
            .scalars()
            .first()
        )

    def search(
        self,
        notice_type: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SystemNotificationEntity], int]:
        """分页查询系统通知（按发布时间倒序）。

        Args:
            notice_type: 通知类型过滤（可选）
            status: 发布状态过滤（可选）
            keyword: 标题/正文关键字搜索（可选）
            skip: 跳过条数
            limit: 返回条数

        Returns:
            tuple[list[SystemNotificationEntity], int]: 实体列表与总条数
        """
        conditions: list[Any] = []
        if notice_type:
            conditions.append(SystemNotificationEntity.notice_type == notice_type)
        if status:
            conditions.append(SystemNotificationEntity.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    SystemNotificationEntity.title.like(pattern),
                    SystemNotificationEntity.content.like(pattern),
                )
            )
        stmt = select(SystemNotificationEntity)
        if conditions:
            stmt = stmt.where(*conditions)
        count_stmt = select(func.count()).select_from(SystemNotificationEntity)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = self._session.execute(count_stmt).scalar() or 0
        rows = (
            self._session.execute(stmt.order_by(SystemNotificationEntity.created_at.desc()).offset(skip).limit(limit))
            .scalars()
            .all()
        )
        return list(rows), total

    def commit(self) -> None:
        """提交当前事务。"""
        self._session.commit()
