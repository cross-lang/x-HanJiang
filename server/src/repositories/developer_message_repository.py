#!/usr/bin/env python3
"""
开发者站内信数据访问实现（开放平台门户域）。
本模块提供开发者站内信表 developer_messages 的 Repository 实现，
与管理系统用户站内信（notification_records + StationMessageRepository）分表隔离。

支持未读数统计、分页查询、标记已读、全部已读、写入（发送）。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    DeveloperMessageRepository: 开发者站内信数据访问 SQLAlchemy 实现
"""

from sqlalchemy import func, select, update

from src.constants.enums import DeveloperMessageStatus
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.repositories.base_repository import BaseRepository


class DeveloperMessageRepository(BaseRepository[DeveloperMessageEntity, int]):
    """开发者站内信数据访问 SQLAlchemy 实现。"""

    model_class = DeveloperMessageEntity

    def _developer_query(self, developer_id: int):
        """站内信基础查询（按收件开发者过滤，排除软删除）。"""
        return select(DeveloperMessageEntity).where(
            DeveloperMessageEntity.developer_id == developer_id,
            DeveloperMessageEntity.deleted_at.is_(None),
        )

    def unread_count(self, developer_id: int) -> int:
        """统计开发者未读站内信数量。"""
        stmt = self._developer_query(developer_id).where(
            DeveloperMessageEntity.status == DeveloperMessageStatus.UNREAD.value
        )
        return self.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0

    def list_messages(
        self,
        developer_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[DeveloperMessageEntity], int]:
        """分页查询开发者站内信（按时间倒序）。"""
        base = self._developer_query(developer_id)
        total = (
            self.session.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
        )
        rows = list(
            self.session.execute(base.order_by(DeveloperMessageEntity.created_at.desc()).offset(skip).limit(limit))
            .scalars()
            .all()
        )
        return rows, total

    def get_message(self, developer_id: int, msg_id: int) -> DeveloperMessageEntity | None:
        """查询开发者某条站内信。"""
        return (
            self.session.execute(self._developer_query(developer_id).where(DeveloperMessageEntity.id == msg_id))
            .scalars()
            .first()
        )

    def mark_read(self, msg: DeveloperMessageEntity) -> None:
        """标记单条已读（实体已由调用方持有，此处仅落状态）。"""
        msg.status = DeveloperMessageStatus.READ.value
        self.session.flush()

    def mark_all_read(self, developer_id: int) -> None:
        """将开发者全部未读站内信标记为已读。"""
        self.session.execute(
            update(DeveloperMessageEntity)
            .where(
                DeveloperMessageEntity.developer_id == developer_id,
                DeveloperMessageEntity.deleted_at.is_(None),
                DeveloperMessageEntity.status == DeveloperMessageStatus.UNREAD.value,
            )
            .values(status=DeveloperMessageStatus.READ.value)
        )
        self.session.flush()
