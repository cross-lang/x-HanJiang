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
from sqlalchemy.orm import Session

from src.core.exceptions import DatabaseException
from src.infras.mysql import get_session_factory
from src.models.entities.user_entity import (
    PermissionEntity,
    RolePermissionEntity,
)
from src.repositories.base_repository import BaseRepository


class RolePermissionRepository(BaseRepository[RolePermissionEntity, int]):
    """角色权限关联数据访问 SQLAlchemy 实现。

    Attributes:
        session: 数据库会话对象
    """

    def __init__(self, session: Session | None = None) -> None:
        """初始化角色权限关联仓库。"""
        self.session: Session = session or get_session_factory()()

    def get_by_id(self, id: int) -> RolePermissionEntity | None:
        """根据关联 ID 查询。"""
        stmt = select(RolePermissionEntity).where(RolePermissionEntity.id == id)
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[RolePermissionEntity]:
        """查询所有关联记录（分页）。"""
        stmt = select(RolePermissionEntity).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        """统计关联记录总数。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(RolePermissionEntity)
        return self.session.execute(stmt).scalar() or 0

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
        """创建关联记录。"""
        return self.add_permission(entity.role_id, entity.permission_id)

    def update(self, id: int, entity: RolePermissionEntity) -> RolePermissionEntity | None:
        """更新关联记录（基类接口，关联表通常无需更新）。"""
        return self.get_by_id(id)

    def delete(self, id: int) -> bool:
        """根据关联 ID 删除记录。"""
        existing = self.get_by_id(id)
        if existing is None:
            return False
        try:
            self.session.delete(existing)
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除关联失败: {e}") from e

    def count(self) -> int:
        """统计关联记录总数（BaseRepository 接口）。"""
        return self.count_all()
