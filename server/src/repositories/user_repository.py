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

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from src.core.exceptions import ConflictException, DatabaseException
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
    UserEntity,
    UserRoleEntity,
)
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
        """根据角色 ID 查询所有关联该角色的未删除用户（多对多）。"""
        stmt = (
            self._base_query()
            .join(UserRoleEntity, UserRoleEntity.user_id == UserEntity.id)
            .where(UserRoleEntity.role_id == role_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_ids(self, user_ids: list[int]) -> list[UserEntity]:
        """按用户 ID 列表批量查询未删除用户（用于定向发布）。

        Args:
            user_ids: 用户 ID 列表

        Returns:
            list[UserEntity]: 命中的未删除用户实体列表
        """
        if not user_ids:
            return []
        stmt = self._base_query().where(UserEntity.id.in_(user_ids))
        return list(self.session.execute(stmt).scalars().all())

    def get_roles_by_user_id(self, user_id: int) -> list[RoleEntity]:
        """查询用户关联的所有角色（含角色编码，用于登录态/详情组装）。"""
        stmt = (
            select(RoleEntity)
            .join(UserRoleEntity, UserRoleEntity.role_id == RoleEntity.id)
            .where(UserRoleEntity.user_id == user_id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_perm_codes_by_role_ids(self, role_ids: list[int]) -> list[str]:
        """根据角色 ID 列表查询去重后的权限编码。"""
        if not role_ids:
            return []
        stmt = (
            select(PermissionEntity.perm_code)
            .join(
                RolePermissionEntity,
                RolePermissionEntity.permission_id == PermissionEntity.id,
            )
            .where(RolePermissionEntity.role_id.in_(role_ids))
        )
        return [r[0] for r in self.session.execute(stmt).all()]

    def get_permissions_by_role_ids(self, role_ids: list[int]) -> list[PermissionEntity]:
        """根据角色 ID 列表查询权限实体（排除已废弃，按 sort_order 排序）。"""
        if not role_ids:
            return []
        stmt = (
            select(PermissionEntity)
            .join(
                RolePermissionEntity,
                RolePermissionEntity.permission_id == PermissionEntity.id,
            )
            .where(
                RolePermissionEntity.role_id.in_(role_ids),
                PermissionEntity.is_deprecated == 0,
            )
            .order_by(PermissionEntity.sort_order)
        )
        return list(self.session.execute(stmt).scalars().all())

    def replace_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        """整体替换用户角色关联（先删后插）。"""
        self.session.execute(delete(UserRoleEntity).where(UserRoleEntity.user_id == user_id))
        for rid in role_ids:
            self.session.add(UserRoleEntity(user_id=user_id, role_id=rid))
        self.session.flush()

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
            conditions.append((UserEntity.username.like(like)) | (UserEntity.email.like(like)))
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
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除用户失败: {e}") from e

    def update_last_login(self, user_id: int, last_login_at: datetime, ip_address: str | None) -> None:
        """更新用户最后登录时间与 IP（登录成功后调用）。"""
        existing = self.get_by_id(user_id)
        if existing is None:
            return
        existing.last_login_at = last_login_at
        existing.last_login_ip = ip_address
        self.session.flush()
