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

from sqlalchemy import select

from src.core.exceptions import ConflictException
from src.models.entities.user_entity import UserEntity
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserEntity, int]):
    """用户数据访问 SQLAlchemy 实现。

    使用 SQLAlchemy ORM 进行数据库操作，支持连接池和事务管理。
    实现了 BaseRepository 定义的全部 CRUD 接口，并扩展查询方法。
    异常处理：唯一约束冲突转换为 ConflictException（HTTP 409）。
    """

    model_class = UserEntity

    def _base_query(self):
        """排除软删除用户。"""
        return select(UserEntity).where(UserEntity.deleted_at.is_(None))

    def _handle_integrity_error(self, error, entity):
        raise ConflictException(
            message="用户名或邮箱已存在",
            details={"error": str(error.orig)},
        )

    # ── 业务查询 ──────────────────────────────────────────

    def get_by_username(self, username: str) -> UserEntity | None:
        """根据用户名查询用户（含软删除，用于唯一性校验）。"""
        stmt = select(UserEntity).where(UserEntity.username == username)
        return self.session.execute(stmt).scalars().first()

    def get_by_email(self, email: str) -> UserEntity | None:
        """根据邮箱查询用户（含软删除，用于唯一性校验）。"""
        stmt = select(UserEntity).where(UserEntity.email == email)
        return self.session.execute(stmt).scalars().first()

    def get_by_role_id(self, role_id: int) -> list[UserEntity]:
        """根据角色 ID 查询所有未删除用户。"""
        stmt = self._base_query().where(UserEntity.role_id == role_id)
        return list(self.session.execute(stmt).scalars().all())

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
        return self._paginate(conditions, skip, limit)

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
