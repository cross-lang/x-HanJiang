#!/usr/bin/env python3
"""开放平台门户应用管理服务（创建/修改应用走申请表审批流）。

应用申请/审批解耦后，门户端对应用的所有写操作（创建、编辑基本信息、调整 scope）
统一转换为向 openapi_app_registrations 表提交一条申请批次：
- 创建：随申请同步创建应用记录（approved=False），审批通过后应用才可被网关放行；
- 修改：仅写申请快照，不直接改动应用表，审批通过后由管理系统把快照落地到应用表。

应用表上的 approved 为应用级授权状态（网关放行门槛）；同一应用同一时刻
至多存在一条 pending 申请，重复提交返回 409。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import (
    AppApprovalStatus,
    AppAuthMode,
    AppOwnerType,
    AppRegistrationType,
    AppStatus,
    NotificationChannel,
    StationMessageStatus,
)
from src.constants.permissions import PermissionCode
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.models.entities.notification_entity import NotificationRecordEntity
from src.repositories.base_repository import BaseRepository
from src.schemas.open_portal.app import (
    OpenAppApprovalResponse,
    OpenAppCreateRequest,
    OpenAppResponse,
    OpenAppScopeApplyRequest,
    OpenAppUpdateRequest,
)
from src.utils import security
from src.utils.openapi_utils import (
    build_scope_dict_list,
    generate_app_id,
    generate_registration_code,
)
from src.utils.security import generate_secret_key

logger = logging.getLogger(__name__)


def _parse_scopes(scopes: str | None) -> list[str]:
    """把逗号分隔的 scope 字符串解析为去空后的列表。

    Returns:
        list[str]: scope 列表；空值返回空列表
    """
    return [s for s in (scopes or "").split(",") if s]


def _join_scopes(scopes: list[str] | None) -> str:
    """把 scope 列表按逗号拼接（数据库落库格式）。"""
    return ",".join(dict.fromkeys(scopes or []))


class DeveloperOpenApiAppService:
    """开发者应用管理服务（门户域，全部写操作走申请审批流）。"""

    def __init__(
        self,
        repo: BaseRepository[OpenApiAppEntity, int],
        registration_repo: BaseRepository[OpenApiAppRegistrationEntity, int],
    ) -> None:
        self._repo = repo
        self._registration_repo = registration_repo
        self._session: Session = repo.session

    # ── 查询 ──────────────────────────────────────────────
    def list_my_apps(
        self,
        developer_id: int,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        """分页查询当前开发者名下的应用（含派生审批状态）。"""
        apps, total = self._repo.search_by_keyword(
            keyword=keyword, owner_type=AppOwnerType.DEVELOPER.value, owner_id=developer_id,
            skip=(page - 1) * page_size, limit=page_size,
        )
        return {
            "items": [self._to_response(a) for a in apps],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_my_app(self, app_id: int, developer_id: int) -> OpenAppResponse:
        """查询当前开发者名下的单个应用详情。"""
        entity = self._require_owned(app_id, developer_id)
        self._require_operable(entity)
        return self._to_response(entity)

    def get_public_scopes(self) -> list[dict[str, Any]]:
        """查询开放平台 scope 目录（创建应用/申请权限时展示给开发者）。

        复用 build_scope_dict_list 完成模块中文名映射（OpenApiScopeModule），
        并附带 sort_order 供前端按模块分组排序展示。
        """
        from src.models.entities.app_entity import OpenApiScopeEntity

        scopes = self._session.execute(
            select(OpenApiScopeEntity)
            .where(OpenApiScopeEntity.is_deprecated.is_(False))
            .order_by(OpenApiScopeEntity.sort_order, OpenApiScopeEntity.id)
        ).scalars().all()
        result = build_scope_dict_list(scopes)
        for item, entity in zip(result, scopes, strict=False):
            item["sort_order"] = entity.sort_order
        return result

    def list_approvals(
        self, app_id: int, developer_id: int
    ) -> list[OpenAppApprovalResponse]:
        """查询应用的全部申请/审批记录（仅限本人名下应用，最新在前）。

        审批历史 = openapi_app_registrations 批次：开发者每次创建/修改申请
        均生成一条批次记录，审批结果（审批人/意见/时间）随批次留痕，
        供"审批记录"入口展示多次申请修改权限的完整轨迹。
        """
        entity = self._require_owned(app_id, developer_id)
        regs = self._registration_repo.list_by_app(entity.id)
        # 审批人姓名（users.id → 姓名快照）
        from src.models.entities.user_entity import UserEntity

        approver_ids = {r.approved_by for r in regs if r.approved_by}
        names: dict[int, str] = {}
        if approver_ids:
            users = self._session.execute(
                select(UserEntity).where(UserEntity.id.in_(approver_ids))
            ).scalars().all()
            names = {u.id: (u.name or u.username or f"管理员#{u.id}") for u in users}
        return [
            OpenAppApprovalResponse(
                id=r.id,
                registration_code=r.registration_code,
                app_id=r.app_id,
                registration_type=r.registration_type,
                name=r.name,
                description=r.description,
                scopes=_parse_scopes(r.scopes),
                auth_mode=r.auth_mode,
                reason=r.apply_reason,
                status=r.status,
                approver_name=names.get(r.approved_by) if r.approved_by else None,
                note=r.approval_note,
                created_at=r.created_at,
                reviewed_at=r.approved_at,
            )
            for r in regs
        ]

    # ── 写操作（全部走申请审批流）─────────────────────────
    def create_app(
        self, developer_id: int, *, payload: OpenAppCreateRequest
    ) -> OpenAppResponse:
        """提交创建应用申请：创建应用记录（approved=False）+ 生成 create 申请批次。

        Raises:
            UnprocessableEntityException: 鉴权模式非法时
            ConflictException: 开发者名下存在同名应用时
        """
        self._validate_auth_mode(payload.auth_mode)
        same_name = self._repo.find_by_name_owner(
            payload.name, AppOwnerType.DEVELOPER.value, developer_id
        )
        if same_name is not None:
            raise ConflictException(message=f"开发者名下已存在名为「{payload.name}」的应用")
        app_id = generate_app_id()
        while self._repo.get_by_app_id(app_id) is not None:
            app_id = generate_app_id()
        # 密钥以哈希 + 加密明文落库（与管理系统同一密钥模型），明文仅生成时刻可用
        app_key_plain = generate_secret_key()
        entity = OpenApiAppEntity(
            name=payload.name,
            description=payload.description,
            app_id=app_id,
            app_key_hash=security.sha256_hex(app_key_plain),
            app_key_encrypted=security.encrypt_text(app_key_plain),
            scopes=_join_scopes(payload.scopes),
            auth_mode=payload.auth_mode,
            status=AppStatus.ACTIVE.value,
            rate_limit_per_minute=60,
            owner_type=AppOwnerType.DEVELOPER.value,
            owner_id=developer_id,
            approved=False,
        )
        self._session.add(entity)
        self._session.flush()
        registration = OpenApiAppRegistrationEntity(
            app_id=entity.id,
            registration_code=self._generate_unique_code(),
            registration_type=AppRegistrationType.CREATE.value,
            name=entity.name,
            description=entity.description,
            scopes=entity.scopes,
            auth_mode=entity.auth_mode,
            status=AppApprovalStatus.PENDING.value,
        )
        self._session.add(registration)
        self._session.flush()
        self._notify_approvers(entity, developer_id, registration.registration_code)
        self._session.commit()
        logger.info("developer %s submitted create-app application app_id=%s", developer_id, entity.app_id)
        return self._to_response(entity)

    def update_app(
        self, app_id: int, developer_id: int, *, payload: OpenAppUpdateRequest
    ) -> OpenAppResponse:
        """提交修改应用申请（基本信息调整，更新类审批通过后快照落地）。

        仅写申请表，不直接修改应用表；存在 pending 申请时返回 409。
        """
        entity = self._require_owned(app_id, developer_id)
        self._require_operable(entity)
        new_name = payload.name or entity.name
        new_description = payload.description or entity.description
        new_auth_mode = payload.auth_mode or entity.auth_mode
        self._validate_auth_mode(new_auth_mode)
        registration = self._submit_update_registration(
            entity,
            developer_id,
            name=new_name,
            description=new_description,
            scopes=_parse_scopes(entity.scopes),
            auth_mode=new_auth_mode,
            reason=None,
        )
        self._session.commit()
        logger.info("developer %s submitted update-app application reg_id=%s", developer_id, registration.id)
        return self._to_response(entity)

    def apply_scopes(
        self, app_id: int, developer_id: int, *, payload: OpenAppScopeApplyRequest
    ) -> OpenAppResponse:
        """提交权限范围调整申请（scope 变更，审批通过后快照落地）。"""
        entity = self._require_owned(app_id, developer_id)
        self._require_operable(entity)
        registration = self._submit_update_registration(
            entity,
            developer_id,
            name=entity.name,
            description=entity.description,
            scopes=payload.scopes,
            auth_mode=entity.auth_mode,
            reason=payload.reason,
        )
        self._session.commit()
        logger.info("developer %s submitted scope application reg_id=%s", developer_id, registration.id)
        return self._to_response(entity)

    def rotate_key(self, app_id: int, developer_id: int) -> dict[str, str]:
        """重置应用 AppKey（即时生效，不涉及审批）。"""
        entity = self._require_owned(app_id, developer_id)
        self._require_operable(entity)
        new_plain = generate_secret_key()
        entity.app_key_hash = security.sha256_hex(new_plain)
        entity.app_key_encrypted = security.encrypt_text(new_plain)
        self._session.commit()
        logger.info("developer %s rotated app key app_id=%s", developer_id, app_id)
        return {"app_id": entity.app_id, "app_key": new_plain}

    def delete_app(self, app_id: int, developer_id: int) -> None:
        """软删除应用，并将该应用待审批的申请置为已驳回（保留历史批次）。"""
        entity = self._require_owned(app_id, developer_id)
        entity.deleted_at = datetime.now(UTC)
        pending = self._registration_repo.find_pending_by_app(entity.id)
        if pending is not None:
            pending.status = AppApprovalStatus.REJECTED.value
            pending.approval_note = "应用已被开发者删除，申请作废"
            pending.approved_at = datetime.now(UTC)
        self._session.commit()
        logger.info("developer %s deleted app_id=%s", developer_id, app_id)

    # ── 内部辅助 ──────────────────────────────────────────
    def _generate_unique_code(self) -> str:
        """生成全局唯一的 6 位数字申请码（碰撞时重试，上限 20 次）。"""
        for _ in range(20):
            code = generate_registration_code()
            if not self._registration_repo.code_exists(code):
                return code
        raise ConflictException(message="申请码生成失败，请稍后重试")
    def _submit_update_registration(
        self,
        entity: OpenApiAppEntity,
        developer_id: int,
        *,
        name: str,
        description: str,
        scopes: list[str],
        auth_mode: str,
        reason: str | None,
    ) -> OpenApiAppRegistrationEntity:
        """提交一条 update 类型申请批次（校验 pending 冲突并通知审批人）。"""
        pending = self._registration_repo.find_pending_by_app(entity.id)
        if pending is not None:
            raise ConflictException(
                message=f"应用「{entity.name}」已有待审批的申请（申请码：{pending.registration_code}），"
                "请等待审批完成后再次提交"
            )
        registration = OpenApiAppRegistrationEntity(
            app_id=entity.id,
            registration_code=self._generate_unique_code(),
            registration_type=AppRegistrationType.UPDATE.value,
            name=name,
            description=description,
            scopes=_join_scopes(scopes),
            auth_mode=auth_mode,
            apply_reason=(reason or "").strip() or None,
            status=AppApprovalStatus.PENDING.value,
        )
        self._session.add(registration)
        self._session.flush()
        self._notify_approvers(entity, developer_id, registration.registration_code)
        return registration

    def _require_owned(self, app_id: int, developer_id: int) -> OpenApiAppEntity:
        """校验应用存在、未被删除且归属当前开发者，否则抛异常。"""
        entity = self._repo.get_by_id(app_id)
        if entity is None:
            raise NotFoundException(message="应用不存在或已被删除")
        if (
            entity.owner_type != AppOwnerType.DEVELOPER.value
            or entity.owner_id != developer_id
        ):
            raise NotFoundException(message="应用不存在或已被删除")
        return entity

    def _require_operable(self, entity: OpenApiAppEntity) -> None:
        """禁用中的应用禁止除删除外的任何写操作。"""
        if entity.status == AppStatus.DISABLED.value:
            raise ConflictException(message="应用已被管理员禁用，无法执行该操作")

    @staticmethod
    def _validate_auth_mode(auth_mode: str) -> None:
        """校验鉴权模式枚举合法性。

        Raises:
            ValidationException: 鉴权模式不在枚举范围内时
        """
        if auth_mode not in {m.value for m in AppAuthMode}:
            raise ValidationException(message=f"不支持的鉴权模式: {auth_mode}")

    def _to_response(self, entity: OpenApiAppEntity) -> OpenAppResponse:
        """将应用实体转换为响应 DTO（审批状态由申请表派生）。"""
        pending = self._registration_repo.find_pending_by_app(entity.id)
        if pending is not None:
            approval_status = AppApprovalStatus.PENDING.value
            pending_registration_id = pending.id
        elif entity.approved:
            approval_status = AppApprovalStatus.APPROVED.value
            pending_registration_id = None
        else:
            latest = self._registration_repo.find_latest_by_app(entity.id)
            approval_status = (
                latest.status if latest is not None else None
            )
            pending_registration_id = None
        return OpenAppResponse(
            id=entity.id,
            app_id=entity.app_id,
            name=entity.name,
            description=entity.description,
            scopes=_parse_scopes(entity.scopes),
            auth_mode=entity.auth_mode,
            status=entity.status,
            owner_type=entity.owner_type,
            owner_id=entity.owner_id,
            approved=entity.approved,
            approval_status=approval_status,
            pending_registration_id=pending_registration_id,
            last_used_at=entity.last_used_at,
            created_at=entity.created_at,
        )

    def _notify_approvers(
        self,
        app: OpenApiAppEntity,
        developer_id: int,
        registration_code: str,
    ) -> None:
        """站内信通知拥有应用审批权限的管理员（超级管理员自动具备）。

        与管理端站内信同一模型（notification_records 一条消息一条记录）：
        channel=station / recipient=user:{id} / subject+content 渲染正文。
        通知失败不影响主流程（随本事务提交）。
        """
        admin_ids = self._repo.list_user_ids_by_perm(PermissionCode.OPENAPI_APP_APPROVE.mark)
        if not admin_ids:
            logger.warning("no approver found for openapi app registration %s", registration_code)
            return
        for admin_id in admin_ids:
            self._session.add(
                NotificationRecordEntity(
                    event_type="openapi_app_registration",
                    channel=NotificationChannel.STATION.value,
                    recipient=f"user:{admin_id}",
                    subject="开放应用申请待审批",
                    content=(
                        f"开发者提交了应用「{app.name}」的申请（申请码：{registration_code}），"
                        "请前往 开放平台 → 应用审批 查看并处理。"
                    ),
                    status=StationMessageStatus.UNREAD.value,
                    retry_count=0,
                    max_retries=0,
                )
            )
