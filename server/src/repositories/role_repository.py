#!/usr/bin/env python3
"""
角色数据访问实现

本模块提供角色 Repository 的 SQLAlchemy 数据库实现。
支持按角色编码、角色名称等条件查询。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    RoleRepository: 角色数据访问 SQLAlchemy 实现
"""

from datetime import datetime

from sqlalchemy import select

from src.core.exceptions import ConflictException, DatabaseException
from src.models.entities.user_entity import RoleEntity
from src.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[RoleEntity, int]):
    """角色数据访问 SQLAlchemy 实现。"""

    model_class = RoleEntity

    def _base_query(self):
        """排除软删除角色。"""
        return select(RoleEntity).where(RoleEntity.deleted_at.is_(None))

    def _handle_integrity_error(self, error, entity):
        raise ConflictException(
            message="角色编码或名称已存在",
            details={"error": str(error.orig)},
        )

    # ── 业务查询 ──────────────────────────────────────────

    def get_by_code(self, role_code: str) -> RoleEntity | None:
        """根据角色编码查询角色（含软删除，用于唯一性校验）。"""
        stmt = select(RoleEntity).where(RoleEntity.role_code == role_code)
        return self.session.execute(stmt).scalars().first()

    def get_by_name(self, role_name: str) -> RoleEntity | None:
        """根据角色名称查询角色（含软删除，用于唯一性校验）。"""
        stmt = select(RoleEntity).where(RoleEntity.role_name == role_name)
        return self.session.execute(stmt).scalars().first()

    def search(
        self,
        keyword: str | None = None,
        role_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[RoleEntity], int]:
        """按关键字/类型/状态搜索未删除角色（分页）。"""
        conditions = [RoleEntity.deleted_at.is_(None)]
        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                (RoleEntity.role_name.like(like)) | (RoleEntity.role_code.like(like))
            )
        if role_type:
            conditions.append(RoleEntity.role_type == role_type)
        if status:
            conditions.append(RoleEntity.status == status)
        return self._paginate(conditions, skip, limit)

    def delete(self, id: int) -> bool:
        """软删除角色（设置 deleted_at）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return False
        existing.deleted_at = datetime.now()
        try:
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除角色失败: {e}") from e
