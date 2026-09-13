#!/usr/bin/env python3
"""业务审计服务。"""

from datetime import datetime
from typing import Any

from src.core.logger import logger
from src.models.entities.audit_entity import AuditLogEntity
from src.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    """审计日志服务，记录谁在什么时间改了什么数据。"""

    def __init__(self, audit_log_repository: AuditLogRepository | None = None) -> None:
        self._repository = audit_log_repository or AuditLogRepository()

    def log_event(
        self,
        entity_type: str,
        entity_id: str | int | None,
        action: str,
        operator_id: int | None = None,
        operator_name: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        remarks: str | None = None,
    ) -> AuditLogEntity:
        entity = AuditLogEntity(
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            action=action,
            operator_id=operator_id,
            operator_name=operator_name,
            before_data=before_data,
            after_data=after_data,
            ip_address=ip_address,
            remarks=remarks,
            created_at=datetime.now(),
        )
        try:
            saved = self._repository.create(entity)
            session = getattr(self._repository, "session", None)
            if session is not None:
                session.commit()
            logger.info(
                "Audit log: entity_type=%s entity_id=%s action=%s operator_id=%s",
                entity_type,
                entity_id,
                action,
                operator_id,
            )
            return saved
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Audit log write failed for entity_type=%s entity_id=%s action=%s: %s",
                entity_type,
                entity_id,
                action,
                exc,
            )
            return entity

    def search(
        self,
        entity_type: str | None = None,
        action: str | None = None,
        operator_id: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        skip = (page - 1) * page_size
        items, total = self._repository.search(
            entity_type=entity_type,
            action=action,
            operator_id=operator_id,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_by_id(self, log_id: int) -> AuditLogEntity | None:
        """根据日志 ID 查询单条审计日志。"""
        return self._repository.get_by_id(log_id)
