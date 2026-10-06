"""公告仓库。
仅负责 announcements 表的 CRUD 与分页查询，不含业务判断。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.models.entities.announcement_entity import AnnouncementEntity


class AnnouncementRepository:
    """公告数据访问层。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, entity: AnnouncementEntity) -> AnnouncementEntity:
        """新增公告。

        Args:
            entity: 公告实体

        Returns:
            AnnouncementEntity: 带主键的持久化实体
        """
        self._session.add(entity)
        self._session.flush()
        return entity

    def get_by_id(self, announcement_id: int) -> AnnouncementEntity | None:
        """按主键查询公告。

        Args:
            announcement_id: 公告 ID

        Returns:
            AnnouncementEntity | None: 公告实体或不存在时为 None
        """
        return (
            self._session.execute(select(AnnouncementEntity).where(AnnouncementEntity.id == announcement_id))
            .scalars()
            .first()
        )

    def search(
        self,
        status: str | None = None,
        position: str | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AnnouncementEntity], int]:
        """分页查询公告（按排序权重与创建时间倒序）。

        Args:
            status: 发布状态过滤（可选）
            position: 展示位置过滤（可选）
            keyword: 标题/正文关键字过滤（可选）
            skip: 跳过条数
            limit: 返回条数

        Returns:
            tuple[list[AnnouncementEntity], int]: 实体列表与总条数
        """
        conditions: list[Any] = []
        if status:
            conditions.append(AnnouncementEntity.status == status)
        if position:
            conditions.append(AnnouncementEntity.position == position)
        if keyword:
            like = f"%{keyword}%"
            conditions.append(AnnouncementEntity.title.like(like) | AnnouncementEntity.content.like(like))
        base = select(AnnouncementEntity)
        if conditions:
            base = base.where(*conditions)
        count_stmt = select(func.count()).select_from(AnnouncementEntity)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = self._session.execute(count_stmt).scalar() or 0
        rows = (
            self._session.execute(
                base.order_by(AnnouncementEntity.sort_order.asc(), AnnouncementEntity.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def list_available(self, position: str | None = None, limit: int = 20) -> list[AnnouncementEntity]:
        """查询当前生效中的公告（published 且处于有效期内）。

        Args:
            position: 展示位置过滤（可选）
            limit: 返回条数上限

        Returns:
            list[AnnouncementEntity]: 生效公告列表
        """
        now = datetime.now()
        conditions: list[Any] = [
            AnnouncementEntity.status == "published",
            AnnouncementEntity.start_at <= now,
            AnnouncementEntity.end_at >= now,
        ]
        if position:
            conditions.append(AnnouncementEntity.position == position)
        stmt = select(AnnouncementEntity).where(*conditions)
        rows = (
            self._session.execute(
                stmt.order_by(AnnouncementEntity.sort_order.asc(), AnnouncementEntity.created_at.desc()).limit(limit)
            )
            .scalars()
            .all()
        )
        return list(rows)

    def delete(self, announcement_id: int) -> None:
        """按主键删除公告。

        Args:
            announcement_id: 公告 ID
        """
        self._session.execute(delete(AnnouncementEntity).where(AnnouncementEntity.id == announcement_id))

    def commit(self) -> None:
        """提交当前事务。"""
        self._session.commit()
