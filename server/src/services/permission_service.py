#!/usr/bin/env python3
"""
权限业务逻辑实现

提供权限查询、创建、更新、删除，以及角色权限绑定维护。

Classes:
    PermissionService: 权限业务逻辑实现
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.constants.enums import NotificationEvent
from src.core.exceptions import ConflictException, NotFoundException
from src.core.logger import logger
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
)
from src.repositories.permission_repository import PermissionRepository
from src.repositories.role_permission_repository import RolePermissionRepository
from src.repositories.role_repository import RoleRepository
from src.schemas.role import (
    PermissionResponse,
    RolePermissionResponse,
)
from src.services.base_service import BaseService

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher


class PermissionService(BaseService[PermissionResponse, int, PermissionRepository]):
    """权限业务逻辑实现。

    继承 BaseService 提供的通用能力：
        - get_by_id / get_all / _commit / _audit / _log_action

    本类负责：
        - 权限特有的业务校验（编码唯一性）
        - Entity → PermissionResponse 转换
        - 角色权限绑定管理
    """

    entity_type = "permission"

    def __init__(
        self,
        permission_repository: PermissionRepository,
        role_permission_repository: RolePermissionRepository | None = None,
        role_repository: RoleRepository | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        """初始化权限服务。"""
        self._repository: PermissionRepository = permission_repository
        self._rp_repository = role_permission_repository or RolePermissionRepository(
            session=permission_repository.session
        )
        self._role_repository = role_repository or RoleRepository(
            session=permission_repository.session
        )
        self._dispatcher = dispatcher

    def get_all_modules(self) -> list[str]:
        """返回所有去重的模块列表。"""
        rows = self._repository.session.query(PermissionEntity.module).distinct().all()
        return sorted([r[0] for r in rows])

    def get_all_operations(self) -> list[str]:
        """返回所有去重的操作类型列表。"""
        rows = self._repository.session.query(PermissionEntity.operation).distinct().all()
        return sorted([r[0] for r in rows])

    def search(
        self,
        keyword: str | None = None,
        module: str | None = None,
        operation: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索权限（分页）。"""
        skip = (page - 1) * page_size
        entities, total = self._repository.search(
            keyword=keyword,
            module=module,
            operation=operation,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create(self, data: dict[str, Any], operator: dict[str, Any] | None = None) -> PermissionResponse:
        """创建权限。"""
        perm_code = data.get("perm_code")
        if perm_code and self._repository.get_by_code(perm_code) is not None:
            raise ConflictException(message=f"权限编码 {perm_code} 已存在")

        entity = PermissionEntity(
            perm_code=data["perm_code"],
            perm_name=data["perm_name"],
            module=data.get("module", ""),
            operation=data.get("operation", ""),
            description=data.get("description"),
            sort_order=data.get("sort_order", 0),
        )
        created = self._repository.create(entity)
        self._commit()
        self._audit(
            entity_id=created.id,
            action="create",
            operator=operator,
            before_data=None,
            after_data={"perm_code": created.perm_code, "perm_name": created.perm_name},
            remarks="permission created",
        )
        result = self._to_response(created)
        logger.info(f"Permission created: id={result.id} code={result.perm_code}")
        return result

    def update(self, id: int, data: dict[str, Any], operator: dict[str, Any] | None = None) -> PermissionResponse:
        """更新权限信息。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"权限 {id} 不存在")

        if "perm_code" in data and data["perm_code"] != existing.perm_code:
            other = self._repository.get_by_code(data["perm_code"])
            if other is not None and other.id != id:
                raise ConflictException(
                    message=f"权限编码 {data['perm_code']} 已被其他权限占用"
                )

        patch = PermissionEntity(
            id=id,
            perm_code=existing.perm_code,
            perm_name=existing.perm_name,
            module=existing.module,
            operation=existing.operation,
            description=existing.description,
            sort_order=existing.sort_order,
        )
        for key in ("perm_code", "perm_name", "module", "operation", "description", "sort_order"):
            if key in data:
                setattr(patch, key, data[key])

        updated = self._repository.update(id, patch)
        if updated is None:
            raise NotFoundException(message=f"权限 {id} 不存在")
        self._commit()
        self._audit(
            entity_id=updated.id,
            action="update",
            operator=operator,
            before_data={"perm_code": existing.perm_code, "perm_name": existing.perm_name, "module": existing.module, "operation": existing.operation},
            after_data={"perm_code": updated.perm_code, "perm_name": updated.perm_name, "module": updated.module, "operation": updated.operation},
            remarks="permission updated",
        )
        result = self._to_response(updated)
        logger.info(f"Permission updated: id={result.id} code={result.perm_code}")
        return result

    def delete(self, id: int, operator: dict[str, Any] | None = None) -> bool:
        """删除权限（同时清理角色绑定关系）。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"权限 {id} 不存在")
        self._repository.delete(id)
        self._commit()
        self._audit(
            entity_id=id,
            action="delete",
            operator=operator,
            before_data={"perm_code": existing.perm_code, "perm_name": existing.perm_name, "module": existing.module, "operation": existing.operation},
            after_data=None,
            remarks="permission deleted",
        )
        logger.info(f"Permission deleted: id={id}")
        return True

    def get_role_permissions(self, role_id: int) -> list[RolePermissionResponse]:
        """查询角色权限详情（含权限详情）。"""
        role = self._role_repository.get_by_id(role_id)
        if role is None:
            raise NotFoundException(message=f"角色 {role_id} 不存在")

        entities = self._rp_repository.get_permissions_by_role(role_id)
        return [
            RolePermissionResponse(
                role_id=role_id,
                permission=self._to_response(e),
            )
            for e in entities
        ]

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        """判断用户是否拥有某权限，使用缓存避免反复查库。"""
        from src.infras.cache import get_cached_cache_provider
        from sqlalchemy import select

        from src.models.entities.user_entity import PermissionEntity

        cache_key = f"perm:{user_id}:{permission_code}"
        provider = get_cached_cache_provider()
        cached = provider.get(cache_key)
        if cached is not None:
            return bool(cached)

        from src.repositories.user_repository import UserRepository

        user = UserRepository(session=self._repository.session).get_by_id(user_id)
        if user is None:
            provider.set(cache_key, False, ttl=300)
            return False

        # 从 user_roles 查用户所有角色的权限
        from src.models.entities.user_entity import UserRoleEntity
        role_ids = self._repository.session.query(UserRoleEntity.role_id).filter(
            UserRoleEntity.user_id == user.id
        ).all()
        role_ids = [r[0] for r in role_ids]
        if not role_ids:
            provider.set(cache_key, False, ttl=300)
            return False

        permission_ids = []
        for rid in role_ids:
            permission_ids.extend(self._rp_repository.get_permission_ids_by_role(rid))
        if not permission_ids:
            provider.set(cache_key, False, ttl=300)
            return False

        stmt = select(PermissionEntity.id).where(
            PermissionEntity.id.in_(permission_ids),
            PermissionEntity.perm_code == permission_code,
        )
        allowed = self._repository.session.execute(stmt).scalar() is not None

        provider.set(cache_key, allowed, ttl=300)
        return allowed

    def bind_permission(self, role_id: int, permission_id: int, operator: dict[str, Any] | None = None) -> RolePermissionResponse:
        """为角色绑定权限。"""
        if self._role_repository.get_by_id(role_id) is None:
            raise NotFoundException(message=f"角色 {role_id} 不存在")
        perm = self._repository.get_by_id(permission_id)
        if perm is None:
            raise NotFoundException(message=f"权限 {permission_id} 不存在")

        self._rp_repository.add_permission(role_id, permission_id)
        self._commit()
        self._audit(
            entity_id=role_id,
            action="bind_permission",
            operator=operator,
            before_data={"role_id": role_id, "permission_id": permission_id},
            after_data={"role_id": role_id, "permission_id": permission_id},
            remarks="role permission bound",
        )
        # ── 通知：权限授予 ──
        self._dispatch_permission_event(
            role_id=role_id,
            perm=perm,
            event_type=NotificationEvent.PERMISSION_GRANTED,
        )
        return RolePermissionResponse(
            role_id=role_id, permission=self._to_response(perm)
        )

    def unbind_permission(self, role_id: int, permission_id: int, operator: dict[str, Any] | None = None) -> bool:
        """解除角色与权限的绑定。"""
        perm = self._repository.get_by_id(permission_id)
        result = self._rp_repository.remove_permission(role_id, permission_id)
        if result:
            self._commit()
            self._audit(
                entity_id=role_id,
                action="unbind_permission",
                operator=operator,
                before_data={"role_id": role_id, "permission_id": permission_id},
                after_data=None,
                remarks="role permission unbound",
            )
            # ── 通知：权限回收 ──
            if perm:
                self._dispatch_permission_event(
                    role_id=role_id,
                    perm=perm,
                    event_type=NotificationEvent.PERMISSION_REVOKED,
                )
        return result

    def _to_response(self, entity: PermissionEntity) -> PermissionResponse:
        """实体转响应 DTO。"""
        from src.constants.enums import ModuleCode
        module_label = next(
            (m.desc for m in ModuleCode if m.mark == entity.module),
            entity.module,
        )
        return PermissionResponse(
            id=entity.id,
            perm_code=entity.perm_code,
            perm_name=entity.perm_name,
            module=entity.module,
            module_label=module_label,
            operation=entity.operation,
            description=entity.description,
            sort_order=entity.sort_order,
        )

    def _dispatch_permission_event(
        self,
        role_id: int,
        perm: PermissionEntity,
        event_type: NotificationEvent,
    ) -> None:
        """为角色下的所有用户发送权限变更通知（失败不阻断业务）。"""
        if self._dispatcher is None:
            return

        try:
            from src.repositories.user_repository import UserRepository

            users = UserRepository(session=self._repository.session).get_by_role_id(role_id)
            for user in users:
                try:
                    self._dispatcher.dispatch_for_user(
                        user_id=user.id,
                        event_type=event_type,
                        variables={
                            "username": user.username,
                            "permission_name": perm.perm_name,
                            "permission_code": perm.perm_code,
                        },
                    )
                except Exception as e:
                    logger.warning(f"权限变更通知发送失败: user={user.id} perm={perm.perm_code} error={e}")
        except Exception as e:
            logger.warning(f"权限变更通知批量发送失败: role={role_id} error={e}")
