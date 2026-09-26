#!/usr/bin/env python3
"""
角色权限关联数据访问实现

本模块提供角色权限关联 Repository 的 SQLAlchemy 数据库实现。
核心职责：根据角色 ID 查询其拥有的权限列表，以及维护角色与权限的绑定关系。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    RolePermissionRepository: 角色权限关联数据访问 SQLAlchemy 实现
"""

from sqlalchemy import select

from src.core.exceptions import DatabaseException
from src.models.entities.user_entity import (
    PermissionEntity,
    RolePermissionEntity,
)
from src.repositories.base_repository import BaseRepository


class RolePermissionRepository(BaseRepository[RolePermissionEntity, int]):
    """角色权限关联数据访问 SQLAlchemy 实现。"""

    model_class = RolePermissionEntity

    # ── 业务查询 ──────────────────────────────────────────

    def get_permission_ids_by_role(self, role_id: int) -> list[int]:
        """查询某角色绑定的全部权限 ID 列表。"""
        stmt = select(RolePermissionEntity.permission_id).where(
            RolePermissionEntity.role_id == role_id
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_permissions_by_role(self, role_id: int) -> list[PermissionEntity]:
        """查询某角色绑定的全部权限实体（按排序序号排列）。"""
        stmt = (
            select(PermissionEntity)
            .join(
                RolePermissionEntity,
                RolePermissionEntity.permission_id == PermissionEntity.id,
            )
            .where(RolePermissionEntity.role_id == role_id)
            .order_by(PermissionEntity.sort_order)
        )
        return list(self.session.execute(stmt).scalars().all())

    def add_permission(self, role_id: int, permission_id: int) -> RolePermissionEntity:
        """为角色绑定一个权限。"""
        entity = RolePermissionEntity(role_id=role_id, permission_id=permission_id)
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"绑定权限失败: {e}") from e

    def remove_permission(self, role_id: int, permission_id: int) -> bool:
        """解除角色与某权限的绑定。"""
        stmt = select(RolePermissionEntity).where(
            RolePermissionEntity.role_id == role_id,
            RolePermissionEntity.permission_id == permission_id,
        )
        existing = self.session.execute(stmt).scalars().first()
        if existing is None:
            return False
        try:
            self.session.delete(existing)
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"解绑权限失败: {e}") from e

    def create(self, entity: RolePermissionEntity) -> RolePermissionEntity:
        """创建关联记录（委托 add_permission）。"""
        return self.add_permission(entity.role_id, entity.permission_id)

    def update(self, id: int, entity: RolePermissionEntity) -> RolePermissionEntity | None:
        """关联表通常无需更新，仅回读。"""
        return self.get_by_id(id)
