#!/usr/bin/env python3
"""
权限数据访问实现
本模块提供权限 Repository 的 SQLAlchemy 数据库实现。
支持按模块、操作类型等条件查询。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    PermissionRepository: 权限数据访问 SQLAlchemy 实现
"""

from sqlalchemy import func, select

from src.core.exceptions import ConflictException
from src.models.entities.user_entity import PermissionEntity
from src.repositories.base_repository import BaseRepository


class PermissionRepository(BaseRepository[PermissionEntity, int]):
    """权限数据访问 SQLAlchemy 实现。"""

    model_class = PermissionEntity

    def _handle_integrity_error(self, error, entity):
        raise ConflictException(
            message="权限编码已存在",
            details={"error": str(error.orig)},
        )

    # ── 业务查询 ──────────────────────────────────────────

    def get_by_code(self, perm_code: str) -> PermissionEntity | None:
        """根据权限编码查询权限（用于唯一性校验）。"""
        stmt = select(PermissionEntity).where(PermissionEntity.perm_code == perm_code)
        return self.session.execute(stmt).scalars().first()

    def search(
        self,
        keyword: str | None = None,
        module: str | None = None,
        operation: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[PermissionEntity], int]:
        """按关键字/模块/操作类型搜索权限（分页）。"""
        conditions = [PermissionEntity.is_deprecated.is_(False)]
        if keyword:
            like = f"%{keyword}%"
            conditions.append((PermissionEntity.perm_name.like(like)) | (PermissionEntity.perm_code.like(like)))
        if module:
            conditions.append(PermissionEntity.module == module)
        if operation:
            conditions.append(PermissionEntity.operation == operation)
        total = (
            self.session.execute(
                select(func.count()).select_from(select(self.model_class).where(*conditions).subquery())
            ).scalar()
            or 0
        )
        stmt = (
            select(PermissionEntity)
            .where(*conditions)
            .order_by(PermissionEntity.sort_order.asc(), PermissionEntity.id.asc())
            .offset(skip)
            .limit(limit)
        )
        rows = list(self.session.execute(stmt).scalars().all())
        return rows, total

    def get_all_modules(self) -> list[str]:
        """返回所有去重的模块列表。"""
        rows = self.session.execute(select(PermissionEntity.module).distinct()).all()
        return sorted([r[0] for r in rows])

    def get_all_operations(self) -> list[str]:
        """返回所有去重的操作类型列表。"""
        rows = self.session.execute(select(PermissionEntity.operation).distinct()).all()
        return sorted([r[0] for r in rows])

    def exists_permission_in(self, permission_ids: list[int], perm_code: str) -> bool:
        """判断指定权限编码是否存在于权限 ID 集合中（用于权限判断）。"""
        if not permission_ids:
            return False
        stmt = select(PermissionEntity.id).where(
            PermissionEntity.id.in_(permission_ids),
            PermissionEntity.perm_code == perm_code,
        )
        return self.session.execute(stmt).scalar() is not None
