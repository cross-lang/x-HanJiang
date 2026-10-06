#!/usr/bin/env python3
"""开放平台开发者用户管理业务逻辑（管理端视角）。

职责边界：
- 开发者用户列表（分页/关键词/状态过滤 + 旗下应用数统计）；
- 开发者旗下应用列表（复用 OpenApiAppService.list_apps 的 owner 过滤，
  响应结构与管理端应用管理完全一致）；
- 开发者账号启停（禁用级联禁用其名下应用并驳回待审批申请，发开发者站内信）；
- 开发者账号删除（软删除，级联软删除其名下应用，保留历史审批记录）。
开发者账号的创建/注册在开放平台门户侧完成。
"""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from src.constants.enums import (
    AppOwnerType,
    DeveloperMessageCategory,
    DeveloperMessageStatus,
)
from src.constants.permissions import PermissionAction
from src.core.exceptions import NotFoundException
from src.models.entities.developer_entity import DeveloperEntity
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.repositories.developer_repository import DeveloperRepository
from src.schemas.admin.developer import DeveloperResponse
from src.services.admin.base_service import BaseService, audit_crud
from src.services.admin.openapi_app_service import OpenApiAppService


class DeveloperService(BaseService[DeveloperResponse, int, DeveloperRepository]):
    """管理端开发者用户服务（查询 + 启停 + 删除）。

    继承 BaseService 以获得统一的审计快照与事务提交能力；
    列表类方法自行实现（含旗下应用数统计），不覆盖基类分页查询。
    """

    entity_type = "developer"

    def __init__(self, repository: DeveloperRepository, openapi_app_service: OpenApiAppService) -> None:
        self._repository = repository
        self._openapi_app_service = openapi_app_service

    # ── 查询 ────────────────────────────────────────────

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
            items 为 DeveloperResponse 列表，含旗下应用数。
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.search_by_keyword(
            keyword=keyword,
            status=status,
            skip=skip,
            limit=page_size,
        )
        counts = self._repository.list_app_counts([r.id for r in rows])
        items = [self._to_list_item(r, counts.get(r.id, 0)) for r in rows]
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

    # ── 启停 / 删除 ─────────────────────────────────────

    @audit_crud(PermissionAction.STATUS.mark)
    def update_status(
        self,
        developer_id: int,
        status: str,
        operator: dict[str, Any] | None = None,
    ) -> DeveloperResponse:
        """启用或禁用开发者账号。

        禁用为强操作：级联禁用其名下全部开放应用并驳回待审批申请，
        并向开发者发送站内信告知；启用仅恢复账号登录能力，
        不自动恢复其名下应用的启用状态（由应用管理页单独控制）。

        Args:
            developer_id: 开发者 ID
            status: 目标账号状态（enabled / disabled）
            operator: 操作者信息（用于审计与站内信署名）

        Returns:
            DeveloperResponse: 更新后的开发者信息

        Raises:
            NotFoundException: 开发者不存在
        """
        e = self._require_developer(developer_id)
        if status == e.status:
            return self._to_response(e)
        e.status = status
        if status == "disabled":
            self._openapi_app_service.disable_apps_by_owner(
                owner_type=AppOwnerType.DEVELOPER.value,
                owner_id=developer_id,
            )
            self._notify_developer(e, action="禁用", operator=operator, extra="，其名下开放应用已一并禁用")
        else:
            self._notify_developer(e, action="启用", operator=operator)
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    @audit_crud(PermissionAction.DELETE.mark)
    def delete(self, developer_id: int, operator: dict[str, Any] | None = None) -> bool:
        """删除开发者账号（软删除）。

        级联软删除其名下全部开放应用（AppSecret 停止对外服务）；
        历史审批记录（申请表）保留，开发者站内信历史保留。
        删除不可恢复，操作前须二次确认。

        Args:
            developer_id: 开发者 ID
            operator: 操作者信息（用于审计）

        Returns:
            bool: 删除成功返回 True

        Raises:
            NotFoundException: 开发者不存在
        """
        e = self._require_developer(developer_id)
        self._openapi_app_service.soft_delete_apps_by_owner(
            owner_type=AppOwnerType.DEVELOPER.value,
            owner_id=developer_id,
        )
        e.deleted_at = datetime.now(UTC)
        self._repository.flush()
        self._commit()
        return True

    # ── 内部工具 ────────────────────────────────────────

    def _require_developer(self, developer_id: int) -> DeveloperEntity:
        """按 ID 查询未软删除的开发者，不存在则抛异常。

        Args:
            developer_id: 开发者 ID

        Returns:
            DeveloperEntity: 开发者实体

        Raises:
            NotFoundException: 开发者不存在或已删除
        """
        e = self._repository.get_by_id(developer_id)
        if e is None:
            raise NotFoundException(message=f"开发者 {developer_id} 不存在")
        return e

    def _notify_developer(
        self,
        e: DeveloperEntity,
        *,
        action: str,
        operator: dict[str, Any] | None = None,
        extra: str = "",
    ) -> None:
        """开发者账号启停时发送开发者站内信（失败不影响主流程，随主事务提交）。

        Args:
            e: 开发者实体
            action: 动作描述（启用/禁用）
            operator: 操作者信息（用于署名）
            extra: 追加到正文末尾的补充说明
        """
        op_id = (operator or {}).get("operator_id")
        op_name = (operator or {}).get("operator_name") or f"管理员#{op_id}"
        # 通知构造失败不影响账号启停主流程（消息随主事务一并提交）
        with suppress(Exception):
            self._repository.session.add(
                DeveloperMessageEntity(
                    developer_id=e.id,
                    title=f"开发者账号{action}通知",
                    content=(
                        f"您的开发者账号「{e.username}」已被管理系统{action}"
                        f"（操作人：{op_name}）{extra}，如有疑问请联系管理员。"
                    ),
                    category=DeveloperMessageCategory.NOTIFY.value,
                    status=DeveloperMessageStatus.UNREAD.value,
                )
            )

    # ── Entity → DTO ────────────────────────────────────

    def _to_response(self, e: DeveloperEntity) -> DeveloperResponse:
        """将开发者实体转为响应 DTO（不含旗下应用数）。

        Args:
            e: 开发者实体

        Returns:
            DeveloperResponse: 开发者信息（app_count 取默认值 0）
        """
        return DeveloperResponse(
            id=e.id,
            username=e.username,
            email=e.email,
            name=e.name,
            phone=e.phone,
            certification_type=e.certification_type,
            certification_status=e.certification_status,
            company_name=e.company_name,
            status=e.status,
            app_count=0,
            last_login_at=e.last_login_at,
            created_at=e.created_at,
        )

    def _to_list_item(self, e: DeveloperEntity, app_count: int) -> DeveloperResponse:
        """列表行 DTO：在基础响应上回填旗下应用数。

        Args:
            e: 开发者实体
            app_count: 旗下开放应用数（不含已软删除）

        Returns:
            DeveloperResponse: 带应用数的开发者信息
        """
        item = self._to_response(e)
        if app_count:
            return item.model_copy(update={"app_count": app_count})
        return item


__all__ = ["DeveloperService"]
