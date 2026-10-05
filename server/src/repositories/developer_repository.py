#!/usr/bin/env python3
"""开放平台开发者数据访问。"""

from datetime import datetime

from sqlalchemy import Select, func, select

from src.core.exceptions import ConflictException
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.developer_entity import DeveloperEntity
from src.repositories.base_repository import BaseRepository


class DeveloperRepository(BaseRepository[DeveloperEntity, int]):
    """开发者数据访问，支持软删除。"""

    model_class = DeveloperEntity

    def _base_query(self) -> Select[tuple[DeveloperEntity]]:
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

    def search_by_keyword(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DeveloperEntity], int]:
        """按用户名/邮箱/姓名模糊搜索并分页（不含软删除，按主键升序保证分页稳定）。

        Args:
            keyword: 关键字，匹配 username/email/name 任一字段
            status: 账号状态过滤（enabled/disabled）
            skip: 跳过条数
            limit: 返回条数上限

        Returns:
            (当前页实体列表, 匹配总数)
        """
        base = self._base_query()
        if keyword:
            like = f"%{keyword}%"
            base = base.where(
                DeveloperEntity.username.like(like)
                | DeveloperEntity.email.like(like)
                | DeveloperEntity.name.like(like)
            )
        if status:
            base = base.where(DeveloperEntity.status == status)
        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        stmt = base.order_by(DeveloperEntity.id).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all()), total

    def list_app_counts(self, developer_ids: list[int]) -> dict[int, int]:
        """批量统计每个开发者旗下未软删除的应用数（单次聚合查询，避免 N+1）。

        Args:
            developer_ids: 开发者 ID 列表

        Returns:
            {developer_id: app_count}，无应用的开发者不包含在结果中
        """
        if not developer_ids:
            return {}
        stmt = (
            select(OpenApiAppEntity.owner_id, func.count())
            .where(
                OpenApiAppEntity.owner_type == "developer",
                OpenApiAppEntity.owner_id.in_(developer_ids),
                OpenApiAppEntity.deleted_at.is_(None),
            )
            .group_by(OpenApiAppEntity.owner_id)
        )
        return dict(self.session.execute(stmt).all())
