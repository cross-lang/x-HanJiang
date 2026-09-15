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

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictException, DatabaseException
from src.infras.database import get_cached_database_provider
from src.models.entities.user_entity import RoleEntity
from src.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[RoleEntity, int]):
    """角色数据访问 SQLAlchemy 实现。

    Attributes:
        session: 数据库会话对象
    """

    def __init__(self, session: Session | None = None) -> None:
        """初始化角色仓库。"""
        self.session: Session = session or get_cached_database_provider().get_session_factory()()

    def get_by_id(self, id: int, include_deleted: bool = False) -> RoleEntity | None:
        """根据角色 ID 查询角色（默认排除软删除）。"""
        stmt = select(RoleEntity).where(RoleEntity.id == id)
        if not include_deleted:
            stmt = stmt.where(RoleEntity.deleted_at.is_(None))
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[RoleEntity]:
        """查询所有未删除角色（分页）。"""
        stmt = (
            select(RoleEntity)
            .where(RoleEntity.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        """统计未删除角色总数。"""
        stmt = (
            select(func.count())
            .select_from(RoleEntity)
            .where(RoleEntity.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar() or 0

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

        base = select(RoleEntity).where(*conditions)
        total = (
            self.session.execute(
                select(func.count()).select_from(base.subquery())
            ).scalar()
            or 0
        )
        rows = (
            self.session.execute(base.offset(skip).limit(limit)).scalars().all()
        )
        return list(rows), total

    def create(self, entity: RoleEntity) -> RoleEntity:
        """创建新角色。"""
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except IntegrityError as e:
            self.session.rollback()
            raise ConflictException(
                message="角色编码或名称已存在", details={"error": str(e.orig)}
            ) from e
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"创建角色失败: {e}") from e

    def update(self, id: int, entity: RoleEntity) -> RoleEntity | None:
        """更新角色信息（复制非主键字段到已加载实体）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return None

        mapper = inspect(RoleEntity).columns.keys()
        update_data = {
            k: v
            for k, v in entity.__dict__.items()
            if k in mapper and k not in ("id", "created_at")
        }
        for key, value in update_data.items():
            setattr(existing, key, value)

        try:
            self.session.flush()
            return existing
        except IntegrityError as e:
            self.session.rollback()
            raise ConflictException(
                message="角色编码或名称已被其他角色占用", details={"error": str(e.orig)}
            ) from e
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"更新角色失败: {e}") from e

    def delete(self, id: int) -> bool:
        """软删除角色（设置 deleted_at）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return False
        from datetime import datetime

        existing.deleted_at = datetime.now()
        try:
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除角色失败: {e}") from e

    def count(self) -> int:
        """统计未删除角色总数（BaseRepository 接口）。"""
        return self.count_all()
