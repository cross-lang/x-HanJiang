#!/usr/bin/env python3
"""
权限业务逻辑实现

提供权限查询、创建、更新、删除，以及角色权限绑定维护。

Classes:
    PermissionService: 权限业务逻辑实现
"""

from typing import Any

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


class PermissionService(BaseService[PermissionResponse, int]):
    """权限业务逻辑实现。"""

    def __init__(
        self,
        permission_repository: PermissionRepository,
        role_permission_repository: RolePermissionRepository | None = None,
        role_repository: RoleRepository | None = None,
    ) -> None:
        """初始化权限服务。"""
        self._repository: PermissionRepository = permission_repository
        self._rp_repository = role_permission_repository or RolePermissionRepository(
            session=permission_repository.session
        )
        self._role_repository = role_repository or RoleRepository(
            session=permission_repository.session
        )

    def get_by_id(self, id: int) -> PermissionResponse | None:
        """根据权限 ID 查询权限。"""
        entity = self._repository.get_by_id(id)
        return self._to_response(entity) if entity else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有权限（分页）。"""
        skip = (page - 1) * page_size
        entities = self._repository.get_all(skip=skip, limit=page_size)
        return {
            "items": [self._to_response(e) for e in entities],
            "total": self._repository.count_all(),
            "page": page,
            "page_size": page_size,
        }

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

    def create(self, data: dict[str, Any]) -> PermissionResponse:
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
        result = self._to_response(created)
        logger.info(f"Permission created: id={result.id} code={result.perm_code}")
        return result

    def update(self, id: int, data: dict[str, Any]) -> PermissionResponse:
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
        result = self._to_response(updated)
        logger.info(f"Permission updated: id={result.id} code={result.perm_code}")
        return result

    def delete(self, id: int) -> bool:
        """删除权限（同时清理角色绑定关系）。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"权限 {id} 不存在")
        self._repository.delete(id)
        self._commit()
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

    def bind_permission(self, role_id: int, permission_id: int) -> RolePermissionResponse:
        """为角色绑定权限。"""
        if self._role_repository.get_by_id(role_id) is None:
            raise NotFoundException(message=f"角色 {role_id} 不存在")
        perm = self._repository.get_by_id(permission_id)
        if perm is None:
            raise NotFoundException(message=f"权限 {permission_id} 不存在")

        self._rp_repository.add_permission(role_id, permission_id)
        self._commit()
        return RolePermissionResponse(
            role_id=role_id, permission=self._to_response(perm)
        )

    def unbind_permission(self, role_id: int, permission_id: int) -> bool:
        """解除角色与权限的绑定。"""
        result = self._rp_repository.remove_permission(role_id, permission_id)
        if result:
            self._commit()
        return result

    def _to_response(self, entity: PermissionEntity) -> PermissionResponse:
        """实体转响应 DTO。"""
        return PermissionResponse(
            id=entity.id,
            perm_code=entity.perm_code,
            perm_name=entity.perm_name,
            module=entity.module,
            operation=entity.operation,
            description=entity.description,
            sort_order=entity.sort_order,
        )

    def _commit(self) -> None:
        """提交当前会话事务。"""
        try:
            self._repository.session.commit()
        except Exception as e:  # noqa: BLE001
            self._repository.session.rollback()
            raise e
