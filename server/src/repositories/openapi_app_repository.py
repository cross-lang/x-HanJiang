#!/usr/bin/env python3
"""开放平台应用数据访问。"""

from datetime import datetime

from sqlalchemy import Select, func, select

from src.core.exceptions import ConflictException
from src.models.entities.app_entity import OpenApiAppEntity, OpenApiScopeEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.base_repository import BaseRepository


class OpenApiAppRepository(BaseRepository[OpenApiAppEntity, int]):
    """OpenApiApp 数据访问，支持软删除。"""

    model_class = OpenApiAppEntity

    def _base_query(self) -> Select[tuple[OpenApiAppEntity]]:
        """构造不含已软删除应用的基础查询。

        Returns:
            Select[tuple[OpenApiAppEntity]]: 过滤 deleted_at 为空的查询语句
        """
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

    def search_by_keyword(
        self,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[OpenApiAppEntity], int]:
        """按名称关键字分页查询应用（不含已软删除，按主键升序保证分页稳定）。

        Returns:
            (当前页实体列表, 匹配总数)
        """
        base = self._base_query()
        if keyword:
            base = base.where(OpenApiAppEntity.name.like(f"%{keyword}%"))
        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        stmt = base.order_by(OpenApiAppEntity.id).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all()), total

    def get_owner_user(self, user_id: int) -> UserEntity | None:
        """查询应用所属用户（跨实体只读查询，用于组装 owner 名称）。"""
        return self.session.get(UserEntity, user_id)

    def list_active_scopes(self) -> list[OpenApiScopeEntity]:
        """查询全部未废弃的开放平台 scope（按排序号与主键升序）。"""
        stmt = (
            select(OpenApiScopeEntity)
            .where(OpenApiScopeEntity.is_deprecated.is_(False))
            .order_by(OpenApiScopeEntity.sort_order, OpenApiScopeEntity.id)
        )
        return list(self.session.execute(stmt).scalars().all())

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
