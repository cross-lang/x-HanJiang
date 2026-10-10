#!/usr/bin/env python3
"""开放平台应用数据访问。"""

from datetime import datetime
from typing import Any, NoReturn, cast

from sqlalchemy import Select, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictException
from src.models.entities.app_entity import OpenApiAppEntity, OpenApiScopeEntity
from src.models.entities.developer_entity import DeveloperEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.base_repository import BaseRepository


class OpenApiAppRepository(BaseRepository[OpenApiAppEntity, int]):
    """OpenApiApp 数据访问，支持软删除。"""

    model_class = OpenApiAppEntity

    def _base_query(self) -> Select[tuple[OpenApiAppEntity]]:
        """构造不含已软删除应用的基础查询。

        Returns:
            Select[tuple[OpenApiAppEntity]]: 过滤 deleted_at 为空的查询语句
        """
        return select(OpenApiAppEntity).where(OpenApiAppEntity.deleted_at.is_(None))

    def _handle_integrity_error(self, error: IntegrityError, entity: Any) -> NoReturn:
        raise ConflictException(
            message="AppId 已存在",
            details={"error": str(error.orig)},
        )

    def get_by_app_id(self, app_id: str) -> OpenApiAppEntity | None:
        """按对外 AppId 查询（不含已软删除）。"""
        stmt = self._base_query().where(OpenApiAppEntity.app_id == app_id)
        return self.session.execute(stmt).scalars().first()

    def find_by_name_owner(self, name: str, owner_type: str, owner_id: int) -> OpenApiAppEntity | None:
        """按应用名 + 归属方查询未删除应用（创建应用查重用）。

        Args:
            name: 应用名
            owner_type: 归属类型（developer / admin）
            owner_id: 归属方 ID（developers.id / users.id）

        Returns:
            OpenApiAppEntity | None: 命中记录；不存在返回 None
        """
        stmt = self._base_query().where(
            OpenApiAppEntity.name == name,
            OpenApiAppEntity.owner_type == owner_type,
            OpenApiAppEntity.owner_id == owner_id,
        )
        return self.session.execute(stmt).scalars().first()

    def search_by_keyword(
        self,
        keyword: str | None = None,
        owner_type: str | None = None,
        owner_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[OpenApiAppEntity], int]:
        """按名称关键字分页查询应用（不含已软删除，按主键升序保证分页稳定）。

        归属过滤：传入 owner_type/owner_id 时仅返回该归属方名下的应用
        （开发者门户"只看自己"、管理端按来源筛选共用此入口）。
        审批相关过滤已随申请/审批拆分至 OpenApiAppRegistrationRepository。

        Returns:
            (当前页实体列表, 匹配总数)
        """
        base = self._base_query()
        if keyword:
            base = base.where(OpenApiAppEntity.name.like(f"%{keyword}%"))
        if owner_type:
            base = base.where(OpenApiAppEntity.owner_type == owner_type)
        if owner_id is not None:
            base = base.where(OpenApiAppEntity.owner_id == owner_id)
        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        stmt = base.order_by(OpenApiAppEntity.id).offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all()), total

    def get_owner_user(self, user_id: int) -> UserEntity | None:
        """查询归属管理员用户（owner_type=admin 时组装 owner 名称）。"""
        return self.session.get(UserEntity, user_id)

    def get_owner_developer(self, developer_id: int) -> DeveloperEntity | None:
        """查询归属开发者（owner_type=developer 时组装 owner 名称）。"""
        return self.session.get(DeveloperEntity, developer_id)

    def list_user_ids_by_perm(self, perm_code: str) -> list[int]:
        """查询拥有指定权限码的全部管理系统用户 ID（用于审批通知广播）。

        通过 users → user_roles → roles → role_permissions → permissions 关联，
        仅返回 status=enabled 且未软删除的用户。
        """
        from src.models.entities.user_entity import (
            PermissionEntity,
            RolePermissionEntity,
            UserEntity,
            UserRoleEntity,
        )

        stmt = (
            select(UserEntity.id)
            .join(UserRoleEntity, UserRoleEntity.user_id == UserEntity.id)
            .join(RolePermissionEntity, RolePermissionEntity.role_id == UserRoleEntity.role_id)
            .join(PermissionEntity, PermissionEntity.id == RolePermissionEntity.permission_id)
            .where(
                PermissionEntity.perm_code == perm_code,
                UserEntity.status == "enabled",
                UserEntity.deleted_at.is_(None),
            )
            .distinct()
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_active_scopes(self) -> list[OpenApiScopeEntity]:
        """查询全部未废弃的开放平台 scope（按排序号与主键升序）。"""
        stmt = (
            select(OpenApiScopeEntity)
            .where(OpenApiScopeEntity.is_deprecated.is_(False))
            .order_by(OpenApiScopeEntity.sort_order, OpenApiScopeEntity.id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def touch_last_used(self, app_id: str) -> None:
        """更新最近鉴权时间（异步、失败不影响主流程）。"""
        try:
            app = self.get_by_app_id(app_id)
            if app is not None:
                app.last_used_at = datetime.now()
                self.session.flush()
        except Exception:
            self.session.rollback()

    def soft_delete(self, id: int) -> bool:
        existing = self.get_by_id(id)
        if existing is None:
            return False
        existing.deleted_at = datetime.now()
        self.session.flush()
        return True

    def update_status_by_owner(self, owner_type: str, owner_id: int, status: str) -> int:
        """批量更新某归属方名下全部未删除应用的启用状态。

        用于"禁用/删除开发者账号"的级联操作：开发者账号状态变化时，
        其名下自助应用一并启停，避免账号禁用而应用仍可对外提供服务。

        Args:
            owner_type: 归属类型（developer / admin）
            owner_id: 归属方 ID（developers.id / users.id）
            status: 目标应用状态（active / disabled）

        Returns:
            int: 受影响行数
        """
        stmt = (
            update(OpenApiAppEntity)
            .where(
                OpenApiAppEntity.owner_type == owner_type,
                OpenApiAppEntity.owner_id == owner_id,
                OpenApiAppEntity.deleted_at.is_(None),
            )
            .values(status=status)
        )
        result = cast("CursorResult[Any]", self.session.execute(stmt))
        return result.rowcount or 0

    def soft_delete_by_owner(self, owner_type: str, owner_id: int) -> int:
        """批量软删除某归属方名下全部未删除应用。

        Args:
            owner_type: 归属类型（developer / admin）
            owner_id: 归属方 ID（developers.id / users.id）

        Returns:
            int: 受影响行数
        """
        stmt = (
            update(OpenApiAppEntity)
            .where(
                OpenApiAppEntity.owner_type == owner_type,
                OpenApiAppEntity.owner_id == owner_id,
                OpenApiAppEntity.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now())
        )
        result = cast("CursorResult[Any]", self.session.execute(stmt))
        return result.rowcount or 0
