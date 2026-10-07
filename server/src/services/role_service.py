#!/usr/bin/env python3
"""
角色业务逻辑实现
提供角色查询、创建、更新、删除，以及角色权限绑定关系维护。

Classes:
    RoleService: 角色业务逻辑实现
"""

from typing import Any

from src.constants.permissions import PermissionAction
from src.core.exceptions import ConflictException, NotFoundException
from src.core.logger import logger
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
)
from src.repositories.permission_repository import PermissionRepository
from src.repositories.role_permission_repository import RolePermissionRepository
from src.repositories.role_repository import RoleRepository
from src.schemas.role import (
    PermissionResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from src.services.admin.base_service import BaseService, audit_crud


class RoleService(BaseService[RoleResponse, int, RoleRepository]):
    """角色业务逻辑实现。
    继承 BaseService 提供的通用能力：
        - get_by_id / get_all / _commit / _audit / _log_action
    本类负责：
        - 角色特有的业务校验（编码/名称唯一性）
        - Entity → RoleResponse 转换
        - 角色权限绑定管理
    """

    entity_type = "role"

    def __init__(
        self,
        role_repository: RoleRepository,
        role_permission_repository: RolePermissionRepository | None = None,
        permission_repository: PermissionRepository | None = None,
    ) -> None:
        """初始化角色服务。"""
        self._repository: RoleRepository = role_repository
        self._rp_repository = role_permission_repository or RolePermissionRepository(session=role_repository.session)
        self._permission_repository = permission_repository or PermissionRepository(session=role_repository.session)

    def search(
        self,
        keyword: str | None = None,
        role_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索角色（分页）。"""
        skip = (page - 1) * page_size
        entities, total = self._repository.search(
            keyword=keyword,
            role_type=role_type,
            status=status,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @audit_crud(PermissionAction.CREATE.mark)
    def create(self, data: dict[str, Any], operator: dict[str, Any] | None = None) -> RoleResponse:
        """创建角色。"""
        request = RoleCreateRequest(**data)
        if self._repository.get_by_code(request.role_code) is not None:
            raise ConflictException(message=f"角色编码 {request.role_code} 已存在")
        if self._repository.get_by_name(request.role_name) is not None:
            raise ConflictException(message=f"角色名称 {request.role_name} 已存在")
        entity = RoleEntity(
            role_name=request.role_name,
            role_code=request.role_code,
            description=request.description,
            role_type=request.role_type,
            status=request.status,
        )
        created = self._repository.create(entity)
        self._commit()
        result = self._to_response(created)
        logger.info(f"Role created: id={result.id} code={result.role_code}")
        return result

    @audit_crud(PermissionAction.EDIT.mark)
    def update(self, id: int, data: dict[str, Any], operator: dict[str, Any] | None = None) -> RoleResponse:
        """更新角色信息。系统内置角色不允许修改。"""
        request = RoleUpdateRequest(**data)
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"角色 {id} 不存在")
        self._ensure_editable(existing)
        patch = RoleEntity(
            id=id,
            role_name=existing.role_name,
            role_code=existing.role_code,
            description=existing.description,
            role_type=existing.role_type,
            status=existing.status,
        )
        patch_dict = request.model_dump(exclude_unset=True)
        for key, value in patch_dict.items():
            if hasattr(patch, key):
                setattr(patch, key, value)
        updated = self._repository.update(id, patch)
        if updated is None:
            raise NotFoundException(message=f"角色 {id} 不存在")
        self._commit()
        result = self._to_response(updated)
        logger.info(f"Role updated: id={result.id} code={result.role_code}")
        return result

    @audit_crud(PermissionAction.DELETE.mark)
    def delete(self, id: int, operator: dict[str, Any] | None = None) -> bool:
        """软删除角色。系统内置角色不允许删除；有关联用户的角色不允许删除。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"角色 {id} 不存在")
        self._ensure_editable(existing)
        # 检查是否有关联用户（经仓库）
        user_count = self._repository.count_user_links(id)
        if user_count > 0:
            raise ConflictException(message=f"该角色已关联 {user_count} 个用户，请先解除角色关联后再删除")
        deleted = self._repository.delete(id)
        if deleted:
            self._commit()
            logger.info(f"Role deleted: id={id} code={existing.role_code}")
        return deleted

    def get_permissions(self, role_id: int) -> list[PermissionResponse]:
        """查询角色绑定的权限列表。"""
        if self._repository.get_by_id(role_id) is None:
            raise NotFoundException(message=f"角色 {role_id} 不存在")
        entities = self._rp_repository.get_permissions_by_role(role_id)
        return [self._to_permission_response(e) for e in entities]

    @staticmethod
    def _ensure_editable(entity: RoleEntity) -> None:
        """系统内置角色（role_type=system）禁止编辑、禁用、删除。"""
        if entity.role_type == "system":
            raise ConflictException(message=f"系统内置角色「{entity.role_name}」不允许编辑、禁用或删除")

    def _to_response(self, entity: RoleEntity) -> RoleResponse:
        """实体转响应 DTO。"""
        return RoleResponse(
            id=entity.id,
            role_name=entity.role_name,
            role_code=entity.role_code,
            description=entity.description,
            role_type=entity.role_type,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _to_permission_response(entity: PermissionEntity) -> PermissionResponse:
        """权限实体转响应 DTO。"""
        return PermissionResponse(
            id=entity.id,
            perm_code=entity.perm_code,
            perm_name=entity.perm_name,
            module=entity.module,
            operation=entity.operation,
            description=entity.description,
            sort_order=entity.sort_order,
        )
