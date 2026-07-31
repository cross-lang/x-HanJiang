#!/usr/bin/env python3
"""
用户数据访问实现

本模块提供用户 Repository 的 SQLAlchemy 数据库实现，支持真实数据库存储。
使用 ORM 映射实现数据持久化，符合企业级应用标准。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    UserRepository: 用户数据访问 SQLAlchemy 实现
"""


from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictException, DatabaseException
from src.infras.mysql import get_session_factory
from src.models.entities.user_entity import UserEntity
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserEntity, int]):
    """用户数据访问 SQLAlchemy 实现。

    使用 SQLAlchemy ORM 进行数据库操作，支持连接池和事务管理。
    实现了 BaseRepository 定义的全部 CRUD 接口。
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

    def get_by_id(self, id: int) -> UserEntity | None:
        """根据用户 ID 查询用户实体。"""
        return self.session.get(UserEntity, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserEntity]:
        """查询所有用户（分页）。"""
        stmt = select(UserEntity).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, entity: UserEntity) -> UserEntity:
        """创建新用户。

        Args:
            entity: 已实例化的 UserEntity

        Returns:
            UserEntity: 创建成功的实体（含生成的主键）

        Raises:
            ConflictException: 用户名或邮箱唯一约束冲突时抛出
            DatabaseException: 其他数据库错误时抛出
        """
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
        """更新用户信息。

        将传入实体的字段值复制到从数据库加载出的现有实体，避免覆盖未提供字段。

        Args:
            id: 用户唯一标识
            entity: 含有更新字段的实体

        Returns:
            Optional[UserEntity]: 更新后的实体，不存在时返回 None
        """
        existing = self.session.get(UserEntity, id)
        if existing is None:
            return None

        # 仅复制非主键字段
        update_data = entity.to_dict() if hasattr(entity, "to_dict") else entity.__dict__
        update_data.pop("id", None)
        update_data.pop("created_at", None)
        for key, value in update_data.items():
            if hasattr(existing, key):
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
        """删除用户。"""
        user_entity = self.session.get(UserEntity, id)
        if user_entity is None:
            return False
        self.session.delete(user_entity)
        try:
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除用户失败: {e}") from e

    def count(self) -> int:
        """统计用户总数。"""
        stmt = select(func.count()).select_from(UserEntity)
        result = self.session.execute(stmt).scalar()
        return result or 0
