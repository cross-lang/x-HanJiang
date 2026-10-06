#!/usr/bin/env python3
"""开放平台应用审批业务逻辑（管理端视角，独立于应用管理）。

承接 openapi_app_registrations 表（应用申请/审批批次）的列表、详情与审批动作：
- 开发者每次创建/修改应用提交的申请为一条批次记录（以 id 作为申请ID）；
- 审批通过（create 类置应用 approved=True；update 类将申请快照落地到应用表）；
- 审批驳回仅记录审批意见，不影响应用当前内容；
- 审批结果同步以开发者站内信通知申请方，与审批动作同事务提交。

应用自身信息的管理（CRUD、scope 直接授权、启停、密钥）仍在 OpenApiAppService。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from src.constants.enums import (
    AppApprovalStatus,
    AppOwnerType,
    AppRegistrationType,
    DeveloperMessageCategory,
    DeveloperMessageStatus,
)
from src.constants.permissions import PermissionAction
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.repositories.openapi_app_registration_repository import (
    OpenApiAppRegistrationRepository,
)
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.admin.openapi_app_registration import AppRegistrationResponse
from src.services.admin.base_service import BaseService, audit_crud
from src.utils.openapi_utils import parse_scopes

_REGISTRATION_TYPE_LABELS = {
    AppRegistrationType.CREATE.value: "创建应用",
    AppRegistrationType.UPDATE.value: "修改应用",
}
_APPROVAL_ACTION_LABELS = {
    AppApprovalStatus.APPROVED.value: "通过",
    AppApprovalStatus.REJECTED.value: "驳回",
}


class OpenApiAppRegistrationService(BaseService[AppRegistrationResponse, int, OpenApiAppRegistrationRepository]):
    """开放应用申请/审批服务（按批次管理开发者提交的创建与修改申请）。"""

    entity_type = "openapi_app_registration"

    def __init__(
        self,
        repo: OpenApiAppRegistrationRepository,
        app_repo: OpenApiAppRepository,
    ) -> None:
        self._repository = repo
        self._app_repo = app_repo

    # ── 查询 ────────────────────────────────────────────

    def list_registrations(
        self,
        *,
        keyword: str | None = None,
        registration_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """分页查询应用申请记录（按申请ID倒序，最新批次在前）。

        Args:
            keyword: 按应用 App ID / 应用名模糊搜索
            registration_type: 按申请类型过滤（create 创建申请 / update 修改申请）
            status: 按审批状态过滤（pending / approved / rejected）

        Returns:
            {items, total, page, page_size}，与用户列表等接口分页口径一致。
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.search(
            keyword=keyword,
            registration_type=registration_type,
            status=status,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_registration_response(reg, app) for reg, app in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_registration(self, registration_id: int) -> AppRegistrationResponse:
        """按申请ID查询申请详情（含应用信息），不存在抛 NotFound。"""
        reg, app = self._require_registration(registration_id)
        return self._to_registration_response(reg, app)

    # ── 审批 ────────────────────────────────────────────

    @audit_crud(PermissionAction.APPROVE.mark)
    def review(
        self,
        registration_id: int,
        *,
        approved: bool,
        note: str | None = None,
        operator: dict[str, Any] | None = None,
    ) -> AppRegistrationResponse:
        """审批一条应用申请（通过 / 驳回）。

        通过：
            - create 类：将应用 approved 置 True（内容随申请创建时已按快照写入）；
            - update 类：将申请快照（name/description/scopes/auth_mode）落地到应用表。
        驳回：仅记录审批意见与审批人，应用当前内容不受影响。

        审批结果同步以开发者站内信通知申请方（随本事务一并提交）。

        Raises:
            NotFoundException: 申请或关联应用不存在
            ConflictException: 申请已被处理，或关联应用已删除
        """
        reg, app = self._require_registration(registration_id)
        if reg.status != AppApprovalStatus.PENDING.value:
            raise ConflictException(
                message=f"申请（申请码：{reg.registration_code}）已被处理（当前状态：{reg.status}），不能重复审批"
            )
        target_status = (
            AppApprovalStatus.APPROVED.value if approved else AppApprovalStatus.REJECTED.value
        )
        # 通过时落地应用：create→置授权标记；update→快照整体覆盖应用字段
        if approved:
            if reg.registration_type == AppRegistrationType.CREATE.value:
                app.approved = True
            elif reg.registration_type == AppRegistrationType.UPDATE.value:
                app.name = reg.name
                app.description = reg.description
                app.scopes = reg.scopes
                app.auth_mode = reg.auth_mode
        reg.status = target_status
        if operator and operator.get("operator_id") is not None:
            reg.approved_by = operator["operator_id"]
        reg.approval_note = (note or "").strip() or None
        reg.approved_at = datetime.now(UTC)
        # 开发者自助应用：审批结果写入开发者站内信（随本事务一并提交）
        if app.owner_type == AppOwnerType.DEVELOPER.value and app.owner_id is not None:
            self._notify_developer(app, reg, approved)
        self._repository.flush()
        self._commit()
        return self._to_registration_response(reg, app)

    # ── 内部辅助 ────────────────────────────────────────

    def _require_registration(
        self, registration_id: int
    ) -> tuple[OpenApiAppRegistrationEntity, OpenApiAppEntity]:
        """查询申请记录及其关联应用，不存在/应用已删除抛异常。"""
        reg = self._repository.get_by_id(registration_id)
        if reg is None:
            raise NotFoundException(message=f"申请 {registration_id} 不存在")
        app = self._repository.get_app(reg.app_id)
        if app is None or app.deleted_at is not None:
            raise ConflictException(message="关联应用已被删除，无法审批该申请")
        return reg, app

    def _to_response(self, entity: Any) -> AppRegistrationResponse:
        """基类抽象接口：按申请记录联查应用组装响应（供基类通用查询使用）。

        Args:
            entity: 申请记录实体

        Returns:
            AppRegistrationResponse: 申请响应

        Raises:
            ConflictException: 关联应用缺失或已删除时抛出
        """
        reg = cast(OpenApiAppRegistrationEntity, entity)
        app = self._app_repo.get_by_id(reg.app_id) if reg.app_id is not None else None
        if app is None or app.deleted_at is not None:
            raise ConflictException(message="关联应用已被删除，无法查看该申请")
        return self._to_registration_response(reg, app)

    def _to_registration_response(
        self,
        reg: OpenApiAppRegistrationEntity,
        app: OpenApiAppEntity,
    ) -> AppRegistrationResponse:
        """组装审批列表/详情响应（应用侧信息取当前值，申请内容取快照）。"""
        owner_name: str | None = None
        if app.owner_id is not None:
            if app.owner_type == AppOwnerType.DEVELOPER.value:
                developer = self._app_repo.get_owner_developer(app.owner_id)
                owner_name = developer.name or developer.username if developer else None
            else:
                user = self._app_repo.get_owner_user(app.owner_id)
                owner_name = user.name or user.username if user else None
        return AppRegistrationResponse(
            id=reg.id,
            registration_code=reg.registration_code,
            app_id=reg.app_id,
            app_id_str=app.app_id,
            app_name=app.name,
            owner_name=owner_name,
            owner_type=app.owner_type,
            registration_type=reg.registration_type,
            name=reg.name,
            description=reg.description,
            scopes=parse_scopes(reg.scopes),
            auth_mode=reg.auth_mode,
            apply_reason=reg.apply_reason,
            status=reg.status,
            approved_by=reg.approved_by,
            approval_note=reg.approval_note,
            approved_at=reg.approved_at,
            created_at=reg.created_at,
        )

    def _notify_developer(
        self,
        app: OpenApiAppEntity,
        reg: OpenApiAppRegistrationEntity,
        approved: bool,
    ) -> None:
        """审批结果写入开发者站内信（同事务提交，门户右上角即时可见）。"""
        type_label = _REGISTRATION_TYPE_LABELS.get(reg.registration_type, "应用")
        action_label = _APPROVAL_ACTION_LABELS.get(reg.status, "处理")
        app_ref = f"应用「{app.name}」（App ID：{app.app_id}）"
        note_suffix = f" 审批意见：{reg.approval_note}" if reg.approval_note else ""
        if approved:
            content = (
                f"您提交的「{type_label}」申请（申请码：{reg.registration_code}）已通过审批，"
                f"{app_ref}可正常调用开放接口。{note_suffix}"
            )
        else:
            content = (
                f"您提交的「{type_label}」申请（申请码：{reg.registration_code}）未通过审批，"
                f"请根据审批意见调整后重新提交。{note_suffix}"
            )
        self._repository.session.add(
            DeveloperMessageEntity(
                developer_id=app.owner_id,
                title=f"应用申请{action_label}通知",
                content=content,
                category=DeveloperMessageCategory.AUDIT.value,
                status=DeveloperMessageStatus.UNREAD.value,
            )
        )
