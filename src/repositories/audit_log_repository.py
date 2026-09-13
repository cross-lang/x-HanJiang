#!/usr/bin/env python3
"""业务审计日志仓库。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import DatabaseException
from src.infras.mysql import get_session_factory
from src.models.entities.audit_entity import AuditLogEntity
from src.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLogEntity, int]):
    """审计日志数据访问实现。"""

    def __init__(self, session: Session | None = None) -> None:
        self.session: Session = session or get_session_factory()()

    def get_by_id(self, id: int) -> AuditLogEntity | None:
        stmt = select(AuditLogEntity).where(AuditLogEntity.id == id)
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[AuditLogEntity]:
        stmt = select(AuditLogEntity).order_by(AuditLogEntity.created_at.desc()).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        stmt = select(func.count()).select_from(AuditLogEntity)
        return self.session.execute(stmt).scalar() or 0

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

        base = select(AuditLogEntity).where(*conditions).order_by(AuditLogEntity.created_at.desc())
        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
        rows = self.session.execute(base.offset(skip).limit(limit)).scalars().all()
        return list(rows), total

    def create(self, entity: AuditLogEntity) -> AuditLogEntity:
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except Exception as e:  # noqa: BLE001
            self.session.rollback()
            raise DatabaseException(message=f"创建审计日志失败: {e}") from e

    def update(self, id: int, entity: AuditLogEntity) -> AuditLogEntity | None:
        return self.get_by_id(id)

    def delete(self, id: int) -> bool:
        existing = self.get_by_id(id)
        if existing is None:
            return False
        self.session.delete(existing)
        self.session.flush()
        return True

    def count(self) -> int:
        return self.count_all()
