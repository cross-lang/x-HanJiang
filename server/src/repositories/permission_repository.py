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

from sqlalchemy import select

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
        conditions = []
        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                (PermissionEntity.perm_name.like(like))
                | (PermissionEntity.perm_code.like(like))
            )
        if module:
            conditions.append(PermissionEntity.module == module)
        if operation:
            conditions.append(PermissionEntity.operation == operation)
        return self._paginate(conditions, skip, limit)
