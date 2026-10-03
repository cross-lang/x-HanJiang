#!/usr/bin/env python3
"""开放平台开发者数据访问。"""

from datetime import datetime

from sqlalchemy import select

from src.core.exceptions import ConflictException
from src.models.entities.developer_entity import DeveloperEntity
from src.repositories.base_repository import BaseRepository


class DeveloperRepository(BaseRepository[DeveloperEntity, int]):
    """开发者数据访问，支持软删除。"""

    model_class = DeveloperEntity

    def _base_query(self):
        """排除软删除开发者。"""
        return select(DeveloperEntity).where(DeveloperEntity.deleted_at.is_(None))

    def _handle_integrity_error(self, error, entity):
        raise ConflictException(
            message="用户名或邮箱已存在",
            details={"error": str(error.orig)},
        )

    # ── 业务查询 ──────────────────────────────────────────

    def get_by_username(self, username: str) -> DeveloperEntity | None:
        """根据用户名查询（含软删除，用于唯一性校验）。"""
        stmt = select(DeveloperEntity).where(DeveloperEntity.username == username)
        return self.session.execute(stmt).scalars().first()

    def get_by_email(self, email: str) -> DeveloperEntity | None:
        """根据邮箱查询（含软删除，用于唯一性校验）。"""
        stmt = select(DeveloperEntity).where(DeveloperEntity.email == email)
        return self.session.execute(stmt).scalars().first()

    def update_last_login(self, developer_id: int, last_login_at: datetime) -> None:
        """更新最后登录时间。"""
        e = self.get_by_id(developer_id)
        if e is not None:
            e.last_login_at = last_login_at
