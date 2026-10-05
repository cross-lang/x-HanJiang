#!/usr/bin/env python3
"""开放平台开发者用户管理业务逻辑（管理端视角）。

职责边界：
- 开发者用户列表（分页/关键词/状态过滤 + 旗下应用数统计）；
- 开发者旗下应用列表（复用 OpenApiAppService.list_apps 的 owner 过滤，
  响应结构与管理端应用管理完全一致）。
仅查询能力，开发者账号的创建/注册在开放平台门户侧完成。
"""

from __future__ import annotations

from typing import Any

from src.constants.enums import AppOwnerType
from src.core.exceptions import NotFoundException
from src.models.entities.developer_entity import DeveloperEntity
from src.repositories.developer_repository import DeveloperRepository
from src.schemas.admin.developer import DeveloperAdminResponse
from src.services.admin.openapi_app_service import OpenApiAppService


class DeveloperAdminService:
    """管理端开发者用户查询服务。"""

    def __init__(self, repository: DeveloperRepository, openapi_app_service: OpenApiAppService) -> None:
        self._repository = repository
        self._openapi_app_service = openapi_app_service

    def list_developers(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """分页查询开发者用户列表（不含已软删除）。

        Args:
            keyword: 按用户名/邮箱/姓名模糊搜索
            status: 账号状态过滤（enabled/disabled）
            page: 页码（从 1 起）
            page_size: 每页条数

        Returns:
            {items, total, page, page_size}，与用户列表等接口分页口径一致；
            items 为 DeveloperAdminResponse 列表，含旗下应用数。
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.search_by_keyword(
            keyword=keyword,
            status=status,
            skip=skip,
            limit=page_size,
        )
        counts = self._repository.list_app_counts([r.id for r in rows])
        items = [self._to_response(r, counts.get(r.id, 0)) for r in rows]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_developer_apps(
        self,
        *,
        developer_id: int,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """分页查询指定开发者名下的开放应用（owner 隔离，不含已软删除）。

        Args:
            developer_id: 开发者 ID
            keyword: 按应用名称模糊搜索
            page: 页码（从 1 起）
            page_size: 每页条数

        Returns:
            {items, total, page, page_size}，items 为 OpenApiAppResponse 列表

        Raises:
            NotFoundException: 开发者不存在
        """
        dev = self._repository.get_by_id(developer_id)
        if dev is None:
            raise NotFoundException(message=f"开发者 {developer_id} 不存在")
        return self._openapi_app_service.list_apps(
            keyword=keyword,
            owner_type=AppOwnerType.DEVELOPER.value,
            owner_id=developer_id,
            page=page,
            page_size=page_size,
        )

    # ── Entity → DTO ────────────────────────────────────

    def _to_response(self, e: DeveloperEntity, app_count: int) -> DeveloperAdminResponse:
        return DeveloperAdminResponse(
            id=e.id,
            username=e.username,
            email=e.email,
            name=e.name,
            phone=e.phone,
            certification_type=e.certification_type,
            certification_status=e.certification_status,
            company_name=e.company_name,
            status=e.status,
            app_count=app_count,
            last_login_at=e.last_login_at,
            created_at=e.created_at,
        )


__all__ = ["DeveloperAdminService"]
