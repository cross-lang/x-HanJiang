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

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictException, DatabaseException
from src.infras.mysql import get_session_factory
from src.models.entities.user_entity import PermissionEntity
from src.repositories.base_repository import BaseRepository


class PermissionRepository(BaseRepository[PermissionEntity, int]):
    """权限数据访问 SQLAlchemy 实现。

    Attributes:
        session: 数据库会话对象
    """

    def __init__(self, session: Session | None = None) -> None:
        """初始化权限仓库。"""
        self.session: Session = session or get_session_factory()()

    def get_by_id(self, id: int) -> PermissionEntity | None:
        """根据权限 ID 查询权限。"""
        stmt = select(PermissionEntity).where(PermissionEntity.id == id)
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[PermissionEntity]:
        """查询所有权限（分页）。"""
        stmt = select(PermissionEntity).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        """统计权限总数。"""
        stmt = select(func.count()).select_from(PermissionEntity)
        return self.session.execute(stmt).scalar() or 0

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

        base = select(PermissionEntity).where(*conditions)
        total = (
            self.session.execute(
                select(func.count()).select_from(base.subquery())
            ).scalar()
            or 0
        )
        rows = (
            self.session.execute(
                base.order_by(PermissionEntity.sort_order).offset(skip).limit(limit)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def create(self, entity: PermissionEntity) -> PermissionEntity:
        """创建新权限。"""
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except IntegrityError as e:
            self.session.rollback()
            raise ConflictException(
                message="权限编码已存在", details={"error": str(e.orig)}
            ) from e
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"创建权限失败: {e}") from e

    def update(self, id: int, entity: PermissionEntity) -> PermissionEntity | None:
        """更新权限信息。"""
        existing = self.get_by_id(id)
        if existing is None:
            return None

        update_data = {
            k: v
            for k, v in entity.__dict__.items()
            if k in inspect(PermissionEntity).columns.keys() and k != "id"
        }
        for key, value in update_data.items():
            setattr(existing, key, value)

        try:
            self.session.flush()
            return existing
        except IntegrityError as e:
            self.session.rollback()
            raise ConflictException(
                message="权限编码已被其他权限占用", details={"error": str(e.orig)}
            ) from e
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"更新权限失败: {e}") from e

    def delete(self, id: int) -> bool:
        """删除权限（物理删除）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return False
        try:
            self.session.delete(existing)
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除权限失败: {e}") from e

    def count(self) -> int:
        """统计权限总数（BaseRepository 接口）。"""
        return self.count_all()
