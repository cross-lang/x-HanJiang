#!/usr/bin/env python3
"""
权限业务逻辑实现
提供权限查询、创建、更新、删除，以及角色权限绑定维护。

Classes:
    PermissionService: 权限业务逻辑实现
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.constants.enums import NotificationEvent, SystemRoleCode
from src.core.exceptions import NotFoundException
from src.core.logger import logger
from src.models.entities.user_entity import (
    PermissionEntity,
)
from src.repositories.permission_repository import PermissionRepository
from src.repositories.role_permission_repository import RolePermissionRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
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
        user_repository: UserRepository | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        """初始化权限服务。"""
        self._repository: PermissionRepository = permission_repository
        self._rp_repository = role_permission_repository or RolePermissionRepository(
            session=permission_repository.session
        )
        self._role_repository = role_repository or RoleRepository(session=permission_repository.session)
        self._user_repository = user_repository or UserRepository(session=permission_repository.session)
        self._dispatcher = dispatcher

    def get_all_modules(self) -> list[str]:
        """返回所有去重的模块列表。"""
        return self._repository.get_all_modules()

    def get_all_operations(self) -> list[str]:
        """返回所有去重的操作类型列表。"""
        return self._repository.get_all_operations()

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

        cache_key = f"perm:{user_id}:{permission_code}"
        provider = get_cached_cache_provider()
        cached = provider.get(cache_key)
        if cached is not None:
            return bool(cached)
        # 从 user_roles 查用户所有角色（经仓库）
        user_roles = self._role_repository.get_by_user_id(user_id)
        role_rows = [(r.id, r.role_code) for r in user_roles]
        # 超管短路：拥有 SUPERADMIN 角色则自动拥有所有权限
        if any(code == SystemRoleCode.SUPERADMIN.mark for _, code in role_rows):
            provider.set(cache_key, True, ttl=300)
            return True
        role_ids = [rid for rid, _ in role_rows]
        if not role_ids:
            provider.set(cache_key, False, ttl=300)
            return False
        permission_ids = []
        for rid in role_ids:
            permission_ids.extend(self._rp_repository.get_permission_ids_by_role(rid))
        if not permission_ids:
            provider.set(cache_key, False, ttl=300)
            return False
        allowed = self._repository.exists_permission_in(permission_ids, permission_code)
        provider.set(cache_key, allowed, ttl=300)
        return allowed

    def bind_permission(
        self, role_id: int, permission_id: int, operator: dict[str, Any] | None = None
    ) -> RolePermissionResponse:
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
            remarks="给角色绑定权限",
        )
        # ── 通知：权限授予 ──
        self._dispatch_permission_event(
            role_id=role_id,
            perm=perm,
            event_type=NotificationEvent.PERMISSION_GRANTED,
        )
        return RolePermissionResponse(role_id=role_id, permission=self._to_response(perm))

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
                remarks="解除角色权限绑定",
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
        from src.constants.enums import ApiModuleCode

        module_label = next(
            (m.desc for m in ApiModuleCode if m.mark == entity.module),
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
            users = self._user_repository.get_by_role_id(role_id)
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
