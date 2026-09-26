#!/usr/bin/env python3
"""
业务审计日志仓库。

审计日志为只追加流水，不提供更新操作。

Classes:
    AuditLogRepository: 审计日志数据访问 SQLAlchemy 实现
"""

from datetime import datetime

from sqlalchemy import select

from src.core.exceptions import DatabaseException
from src.models.entities.audit_entity import AuditLogEntity
from src.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLogEntity, int]):
    """审计日志数据访问实现。"""

    model_class = AuditLogEntity

    def _base_query(self):
        """默认按创建时间倒序。"""
        return select(AuditLogEntity).order_by(AuditLogEntity.created_at.desc())

    # ── 业务查询 ──────────────────────────────────────────

    def search(
        self,
        entity_type: str | None = None,
        action: str | None = None,
        operator_id: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLogEntity], int]:
        """按条件搜索审计日志（分页）。"""
        conditions = []
        if entity_type:
            conditions.append(AuditLogEntity.entity_type == entity_type)
        if action:
            conditions.append(AuditLogEntity.action == action)
        if operator_id is not None:
            conditions.append(AuditLogEntity.operator_id == operator_id)
        if start_time:
            conditions.append(AuditLogEntity.created_at >= start_time)
        if end_time:
            conditions.append(AuditLogEntity.created_at <= end_time)
        return self._paginate(conditions, skip, limit)

    def update(self, id: int, entity: AuditLogEntity) -> AuditLogEntity | None:
        """审计日志不可变更，仅回读。"""
        return self.get_by_id(id)
