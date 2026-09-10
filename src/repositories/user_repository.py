#!/usr/bin/env python3
"""
用户数据访问实现

本模块提供用户 Repository 的 SQLAlchemy 数据库实现。
支持软删除（deleted_at）与按关键字/状态过滤查询。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    UserRepository: 用户数据访问 SQLAlchemy 实现
"""

from datetime import datetime

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictException, DatabaseException
from src.infras.mysql import get_session_factory
from src.models.entities.user_entity import UserEntity
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserEntity, int]):
    """用户数据访问 SQLAlchemy 实现。

    使用 SQLAlchemy ORM 进行数据库操作，支持连接池和事务管理。
    实现了 BaseRepository 定义的全部 CRUD 接口，并扩展查询方法。
    异常处理：唯一约束冲突转换为 ConflictException（HTTP 409）。

    Attributes:
        session: 数据库会话对象
    """

    def __init__(self, session: Session | None = None) -> None:
        """初始化用户仓库。

        Args:
            session: SQLAlchemy 数据库会话（可选，未提供时自动创建）
        """
        self.session: Session = session or get_session_factory()()

    def get_by_id(self, id: int, include_deleted: bool = False) -> UserEntity | None:
        """根据用户 ID 查询用户实体（默认排除软删除）。"""
        stmt = select(UserEntity).where(UserEntity.id == id)
        if not include_deleted:
            stmt = stmt.where(UserEntity.deleted_at.is_(None))
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserEntity]:
        """查询所有未删除用户（分页）。"""
        stmt = (
            select(UserEntity)
            .where(UserEntity.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        """统计未删除用户总数。"""
        stmt = (
            select(func.count())
            .select_from(UserEntity)
            .where(UserEntity.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar() or 0

    def get_by_username(self, username: str) -> UserEntity | None:
        """根据用户名查询用户（含软删除，用于唯一性校验）。"""
        stmt = select(UserEntity).where(UserEntity.username == username)
        return self.session.execute(stmt).scalars().first()

    def get_by_email(self, email: str) -> UserEntity | None:
        """根据邮箱查询用户（含软删除，用于唯一性校验）。"""
        stmt = select(UserEntity).where(UserEntity.email == email)
        return self.session.execute(stmt).scalars().first()

    def search(
        self,
        keyword: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[UserEntity], int]:
        """按关键字/状态搜索未删除用户（分页）。

        Args:
            keyword: 关键字（匹配 username 或 email）
            status: 状态过滤
            skip: 偏移量
            limit: 每页数量

        Returns:
            tuple[list[UserEntity], int]: (实体列表, 总数)
        """
        conditions = [UserEntity.deleted_at.is_(None)]
        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                (UserEntity.username.like(like)) | (UserEntity.email.like(like))
            )
        if status:
            conditions.append(UserEntity.status == status)

        base = select(UserEntity).where(*conditions)
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

    def create(self, entity: UserEntity) -> UserEntity:
        """创建新用户。"""
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except IntegrityError as e:
            self.session.rollback()
            raise ConflictException(
                message="用户名或邮箱已存在", details={"error": str(e.orig)}
            ) from e
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"创建用户失败: {e}") from e

    def update(self, id: int, entity: UserEntity) -> UserEntity | None:
        """更新用户信息（复制非主键字段到已加载实体）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return None

        mapper = inspect(UserEntity).columns.keys()
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
                message="用户名或邮箱已被其他用户占用", details={"error": str(e.orig)}
            ) from e
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"更新用户失败: {e}") from e

    def delete(self, id: int) -> bool:
        """软删除用户（设置 deleted_at）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return False
        existing.deleted_at = datetime.now()
        try:
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除用户失败: {e}") from e

    def count(self) -> int:
        """统计未删除用户总数（BaseRepository 接口）。"""
        return self.count_all()
