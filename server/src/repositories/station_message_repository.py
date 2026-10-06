#!/usr/bin/env python3
"""
站内信数据访问实现
本模块提供站内信（station_messages 表）Repository 的 SQLAlchemy 实现。
支持未读数统计、分页查询、标记已读、全部已读、写入站内信。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    StationMessageRepository: 站内信数据访问 SQLAlchemy 实现
"""

from datetime import datetime

from sqlalchemy import func, select, update

from src.models.entities.station_message_entity import StationMessageEntity
from src.repositories.base_repository import BaseRepository


class StationMessageRepository(BaseRepository[StationMessageEntity, int]):
    """站内信数据访问 SQLAlchemy 实现。"""

    model_class = StationMessageEntity

    def _station_query(self, user_id: int) -> select:
        """站内信基础查询（按接收用户过滤）。

        Args:
            user_id: 接收用户 ID

        Returns:
            select: 站内信查询语句
        """
        return select(StationMessageEntity).where(StationMessageEntity.user_id == user_id)

    def unread_count(self, user_id: int) -> int:
        """统计用户未读站内信数量。

        Args:
            user_id: 接收用户 ID

        Returns:
            int: 未读数
        """
        stmt = self._station_query(user_id).where(StationMessageEntity.is_read.is_(False))
        return self.session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0

    def list_messages(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        *,
        source: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        keyword: str | None = None,
    ) -> tuple[list[StationMessageEntity], int]:
        """分页查询用户站内信（按时间倒序），支持来源/日期区间/关键词过滤。

        Args:
            user_id: 接收用户 ID
            skip: 偏移量
            limit: 每页数量
            source: 来源过滤（如 system_notice/station/alert/openapi_app）
            start_date: 接收起始时间（含）
            end_date: 接收截止时间（含）
            keyword: 关键词（匹配标题或正文，模糊搜索）

        Returns:
            tuple[list[StationMessageEntity], int]: (站内信列表, 总数)
        """
        stmt = self._station_query(user_id)
        if source:
            stmt = stmt.where(StationMessageEntity.source == source)
        if start_date is not None:
            stmt = stmt.where(StationMessageEntity.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(StationMessageEntity.created_at <= end_date)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                StationMessageEntity.subject.like(like) | StationMessageEntity.content.like(like)
            )
        total = (
            self.session.execute(select(func.count()).select_from(stmt.subquery())).scalar()
            or 0
        )
        rows = list(
            self.session.execute(
                stmt.order_by(StationMessageEntity.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    def get_message(self, user_id: int, msg_id: int) -> StationMessageEntity | None:
        """查询用户某条站内信。

        Args:
            user_id: 接收用户 ID
            msg_id: 站内信 ID

        Returns:
            StationMessageEntity | None: 站内信实体
        """
        return (
            self.session.execute(
                self._station_query(user_id).where(StationMessageEntity.id == msg_id)
            )
            .scalars()
            .first()
        )

    def mark_read(self, msg: StationMessageEntity) -> None:
        """标记单条已读（实体已由调用方持有，此处仅落状态）。

        Args:
            msg: 站内信实体
        """
        msg.is_read = True
        msg.read_at = datetime.now()
        self.session.flush()

    def mark_all_read(self, user_id: int) -> None:
        """将用户全部未读站内信标记为已读。

        Args:
            user_id: 接收用户 ID
        """
        now = datetime.now()
        self.session.execute(
            update(StationMessageEntity)
            .where(
                StationMessageEntity.user_id == user_id,
                StationMessageEntity.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        self.session.flush()

    def create_messages(self, messages: list[StationMessageEntity]) -> None:
        """批量写入站内信（单事务一次提交，供系统通知广播使用）。

        Args:
            messages: 站内信实体列表
        """
        for message in messages:
            self.session.add(message)
        self.session.flush()

    @staticmethod
    def _entity_name() -> str:
        return "站内信"
