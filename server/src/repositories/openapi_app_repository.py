#!/usr/bin/env python3
"""开放平台应用数据访问。"""

from datetime import datetime

from sqlalchemy import select

from src.core.exceptions import ConflictException
from src.models.entities.app_entity import OpenApiAppEntity
from src.repositories.base_repository import BaseRepository


class OpenApiAppRepository(BaseRepository[OpenApiAppEntity, int]):
    """OpenApiApp 数据访问，支持软删除。"""

    model_class = OpenApiAppEntity

    def _base_query(self):
        return select(OpenApiAppEntity).where(OpenApiAppEntity.deleted_at.is_(None))

    def _handle_integrity_error(self, error, entity):
        raise ConflictException(
            message="AppId 已存在",
            details={"error": str(error.orig)},
        )

    def get_by_app_id(self, app_id: str) -> OpenApiAppEntity | None:
        """按对外 AppId 查询（不含已软删除）。"""
        stmt = self._base_query().where(OpenApiAppEntity.app_id == app_id)
        return self.session.execute(stmt).scalars().first()

    def touch_last_used(self, app_id: str) -> None:
        """更新最近鉴权时间（异步、失败不影响主流程）。"""
        try:
            app = self.get_by_app_id(app_id)
            if app is not None:
                app.last_used_at = datetime.now()
                self.session.flush()
        except Exception:
            self.session.rollback()

    def soft_delete(self, id: int) -> bool:
        existing = self.get_by_id(id)
        if existing is None:
            return False
        existing.deleted_at = datetime.now()
        self.session.flush()
        return True
