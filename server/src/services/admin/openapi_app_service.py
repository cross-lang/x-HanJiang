#!/usr/bin/env python3
"""开放平台应用管理业务逻辑（管理端视角）。

仅包含管理员侧的应用 CRUD、密钥生成与重置、scope 直接授权（OpenApiAppService）。
应用申请/审批（创建申请、修改申请批次）由 OpenApiAppRegistrationService 独立承接，
本服务不再承载审批字段与审批动作；应用级授权状态以 approved 标记为准。

- 管理端自建应用（owner_type=admin）：无审批概念，创建即 approved=True；
- 开发者自助应用（owner_type=developer）：须经审批通过（approved=True）方可被网关放行，
  创建/修改申请与审批记录在 openapi_app_registrations 表。

网关鉴权（X-App-Id/App-Key 明文 或 HanJiang-1 签名 + 授权门槛）位于
src/services/open/gateway_service.py（开放接口域）；
公共工具（generate_app_id / parse_scopes / scope 目录映射）在 src/utils/openapi_utils.py。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.constants.enums import (
    AppApprovalStatus,
    AppOwnerType,
    AppStatus,
    DeveloperMessageCategory,
    DeveloperMessageStatus,
    NotificationEvent,
    NotificationSource,
)
from src.constants.permissions import PermissionAction
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.models.entities.station_message_entity import StationMessageEntity
from src.repositories.openapi_app_registration_repository import (
    OpenApiAppRegistrationRepository,
)
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.admin.openapi_app import OpenApiAppResponse
from src.services.admin.base_service import BaseService, audit_crud
from src.utils import security
from src.utils.openapi_utils import (
    build_scope_dict_list,
    generate_app_id,
    parse_scopes,
    validate_scopes,
)
from src.utils.security import generate_secret_key


class OpenApiAppService(BaseService[OpenApiAppResponse, int, OpenApiAppRepository]):
    """开放应用管理（应用自身信息 CRUD；审批动作见 OpenApiAppRegistrationService）。"""

    entity_type = "openapi_app"

    def __init__(
        self,
        repo: OpenApiAppRepository,
        registration_repo: OpenApiAppRegistrationRepository,
    ) -> None:
        self._repository = repo
        self._registration_repo = registration_repo

    # ── 创建 ────────────────────────────────────────────

    @audit_crud(PermissionAction.CREATE.mark)
    def create_app(
        self,
        *,
        name: str,
        description: str,
        scopes: list[str],
        rate_limit_per_minute: int,
        auth_mode: str,
        owner_type: str = AppOwnerType.ADMIN.value,
        owner_id: int | None = None,
        operator: dict[str, Any] | None = None,
    ) -> tuple[OpenApiAppResponse, str]:
        """新建应用，返回 (DTO, 明文 AppKey)。明文 AppKey 仅此次返回。

        Args:
            owner_type: 归属类型（admin=管理员分配，默认；developer=开发者自助，走开发者域接口）
            owner_id: 归属方 ID（admin→users.id / developer→developers.id）

        管理端入口创建的开发者应用仅出现在特殊分配场景：管理端直接代建即视为
        已授权（approved=True），不额外走审批流；开发者门户自助创建才进入审批流。
        """
        validate_scopes(scopes)
        app_id = generate_app_id()
        while self._repository.get_by_app_id(app_id) is not None:
            app_id = generate_app_id()
        app_key_plain = generate_secret_key()
        entity = OpenApiAppEntity(
            app_id=app_id,
            app_key_hash=security.sha256_hex(app_key_plain),
            app_key_encrypted=security.encrypt_text(app_key_plain),
            name=name,
            description=description,
            scopes=",".join(scopes),
            rate_limit_per_minute=rate_limit_per_minute,
            auth_mode=auth_mode,
            owner_type=owner_type,
            owner_id=owner_id,
            approved=True,
            status=AppStatus.ACTIVE.value,
        )
        created = self._repository.create(entity)
        self._commit()
        return self._to_response(created), app_key_plain

    # ── 查询 ────────────────────────────────────────────

    def list_scopes(self) -> list[dict[str, Any]]:
        """查询全部可用（未废弃）的开放平台 scope，供前端创建应用时勾选。

        Returns:
            list[dict[str, Any]]: scope 列表，含模块中文名映射
        """
        entities = self._repository.list_active_scopes()
        return build_scope_dict_list(entities)

    def list_apps(
        self,
        keyword: str | None = None,
        owner_type: str | None = None,
        owner_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """分页查询应用列表（不含已软删除），仅返回应用自身信息。

        Args:
            keyword: 按名称模糊搜索
            owner_type: 按归属类型过滤（developer 开发者自助 / admin 管理员分配）
            owner_id: 按归属方 ID 过滤（与 owner_type 组合，如查询某开发者名下的应用）

        Returns:
            {items, total, page, page_size}，与用户列表等接口分页口径一致。
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.search_by_keyword(
            keyword=keyword,
            owner_type=owner_type,
            owner_id=owner_id,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_response(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_by_id(self, id: int) -> OpenApiAppResponse:
        """根据 ID 查询应用详情，不存在抛 NotFound。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        return self._to_response(e)

    # ── 更新 ────────────────────────────────────────────

    @audit_crud(PermissionAction.EDIT.mark)
    def update(self, id: int, patch: dict[str, Any], operator: dict[str, Any] | None = None) -> OpenApiAppResponse:
        """更新应用基本信息（不含 scopes / status，走专用方法）。

        应用存在待审批申请时拒绝直接编辑，避免管理端改动与申请快照冲突，
        需先在"应用审批"页处理完待审批批次。
        """
        e = self._require_app(id)
        self._reject_if_pending(e)
        for k, v in patch.items():
            if v is not None and hasattr(e, k):
                setattr(e, k, v)
        self._notify_owner_action(
            e,
            action="编辑",
            event=NotificationEvent.OPENAPI_APP_UPDATED,
            operator=operator,
        )
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    @audit_crud(PermissionAction.SCOPES.mark)
    def update_scopes(self, id: int, scopes: list[str], operator: dict[str, Any] | None = None) -> OpenApiAppResponse:
        """覆盖更新应用 scope 列表（管理端直接授权，即时生效，不产生申请批次）。

        与 update 相同：应用存在待审批申请时拒绝直接修改，避免与申请快照冲突。
        """
        validate_scopes(scopes)
        e = self._require_app(id)
        self._reject_if_pending(e)
        e.scopes = ",".join(scopes)
        self._notify_owner_action(
            e,
            action="授权范围变更",
            event=NotificationEvent.OPENAPI_APP_UPDATED,
            operator=operator,
        )
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    @audit_crud(PermissionAction.STATUS.mark)
    def update_status(self, id: int, status: str, operator: dict[str, Any] | None = None) -> OpenApiAppResponse:
        """启用或禁用应用。

        状态变更（尤其禁用）影响应用归属方的实际调用能力，须站内信通知 owner：
        developer 归属发开发者站内信，admin 归属发管理端站内信；
        操作者对自己名下的应用操作不通知（自管自用无需打扰）。

        禁用语义强化：应用存在待审批（pending）的申请批次时，禁用将把该批次
        一并置为已驳回（rejected），避免申请悬空——前端弹窗已向操作者明示此后果。
        """
        e = self._require_app(id)
        e.status = status
        approval_rejected = False
        if status != AppStatus.ACTIVE.value:
            pending = self._registration_repo.find_pending_by_app(e.id)
            if pending is not None:
                pending.status = AppApprovalStatus.REJECTED.value
                pending.approval_note = "应用被管理员禁用，其待审批的申请已一并驳回。"
                pending.approved_at = datetime.now(UTC)
                approval_rejected = True
        self._notify_owner_action(
            e,
            action="禁用" if status != AppStatus.ACTIVE.value else "启用",
            event=NotificationEvent.OPENAPI_APP_UPDATED,
            operator=operator,
            content_suffix=(
                "，其待审批的申请已一并驳回。" if approval_rejected else None
            ),
        )
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    # ── 重置 AppKey（轮换）────────────────────────────

    def rotate_key(self, id: int) -> tuple[OpenApiAppResponse, str]:
        """重置 AppKey：旧 key 立即失效，返回新明文（仅一次）。

        Raises:
            ConflictException: 开发者自助应用由开发者在门户端自助重置，管理端不代操作
        """
        e = self._require_app(id)
        self._reject_developer_app(e, "重置密钥")
        new_plain = generate_secret_key()
        e.app_key_hash = security.sha256_hex(new_plain)
        e.app_key_encrypted = security.encrypt_text(new_plain)
        self._repository.flush()
        self._commit()
        self._log_action(PermissionAction.ROTATE_KEY.mark, id, app_id=e.app_id)
        return self._to_response(e), new_plain

    # ── 删除 ────────────────────────────────────────────

    @audit_crud(PermissionAction.DELETE.mark)
    def delete(self, id: int, operator: dict[str, Any] | None = None) -> bool:
        """删除应用（软删除）。

        Raises:
            ConflictException: 开发者自助应用由开发者在门户端自助删除，管理端不代操作
        """
        e = self._require_app(id)
        self._reject_developer_app(e, "删除")
        self._notify_owner_action(
            e,
            action="删除",
            event=NotificationEvent.OPENAPI_APP_DELETED,
            operator=operator,
        )
        ok = self._repository.soft_delete(id)
        self._commit()
        return ok

    # ── 内部辅助 ────────────────────────────────────────

    def _require_app(self, id: int) -> OpenApiAppEntity:
        """查询应用，不存在抛 NotFound。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        return e

    def _reject_if_pending(self, e: OpenApiAppEntity) -> None:
        """应用存在待审批申请时抛冲突异常（管理端直接修改与申请快照冲突）。"""
        pending = self._registration_repo.find_pending_by_app(e.id)
        if pending is not None:
            raise ConflictException(
                message=f"应用「{e.name}」存在待审批的申请（申请ID：{pending.id}），"
                "请先在 开放平台 → 应用审批 中处理后再编辑"
            )

    @staticmethod
    def _reject_developer_app(e: OpenApiAppEntity, action: str) -> None:
        """开发者自助应用的管理权限归开发者本人，管理端不代操作密钥重置/删除。

        Raises:
            ConflictException: 应用为开发者自助归属（owner_type=developer）时
        """
        if e.owner_type == AppOwnerType.DEVELOPER.value:
            raise ConflictException(
                message=f"应用「{e.name}」为开发者自助应用，请由开发者在开放平台门户自行{action}"
            )

    # ── 归属方站内信通知 ────────────────────────────────

    def _notify_owner_action(
        self,
        e: OpenApiAppEntity,
        *,
        action: str,
        event: NotificationEvent,
        operator: dict[str, Any] | None = None,
        content_suffix: str | None = None,
    ) -> None:
        """禁用/删除等影响应用归属方的操作，站内信通知应用 owner。

        - developer 归属 → 开发者站内信（developer_messages）
        - admin 归属   → 管理端站内信（station_messages）
        操作者本人对自己名下的应用操作不通知（自管自用无需打扰）；
        通知失败不影响主流程（随本事务提交）。
        content_suffix 追加在正文末尾（如"其待审批的申请已一并驳回"）。
        """
        op_id = (operator or {}).get("operator_id")
        op_name = (operator or {}).get("operator_name") or f"管理员#{op_id}"
        # 自己操作自己的应用 → 无需通知
        if e.owner_id is not None and op_id == e.owner_id and e.owner_type == AppOwnerType.ADMIN.value:
            return
        app_ref = f"应用「{e.name}」（App ID：{e.app_id}）"
        suffix = f"{content_suffix}" if content_suffix else ""
        try:
            if e.owner_type == AppOwnerType.DEVELOPER.value and e.owner_id is not None:
                self._repository.session.add(
                    DeveloperMessageEntity(
                        developer_id=e.owner_id,
                        title=f"应用{action}通知",
                        content=(
                            f"{app_ref}已被管理系统{action}（操作人：{op_name}）"
                            f"{suffix}，如有疑问请联系管理员。"
                        ),
                        category=DeveloperMessageCategory.NOTIFY.value,
                        status=DeveloperMessageStatus.UNREAD.value,
                    )
                )
            elif e.owner_type == AppOwnerType.ADMIN.value and e.owner_id is not None:
                self._repository.session.add(
                    StationMessageEntity(
                        user_id=e.owner_id,
                        subject=f"【开放平台】应用{action}通知",
                        content=f"{app_ref}已被{op_name}{action}{suffix}，如有疑问请联系管理员。",
                        source=NotificationSource.OPENAPI_APP.value,
                        event_type=event.mark,
                        is_read=False,
                    )
                )
        except Exception:
            # 通知构造失败不影响应用主流程（消息随主事务一并提交，无需单独 flush）
            pass

    # ── Entity → DTO ────────────────────────────────────

    def _to_response(self, e: OpenApiAppEntity) -> OpenApiAppResponse:
        owner_name = None
        if e.owner_id is not None:
            if e.owner_type == AppOwnerType.DEVELOPER.value:
                developer = self._repository.get_owner_developer(e.owner_id)
                owner_name = developer.name or developer.username if developer else None
            else:
                user = self._repository.get_owner_user(e.owner_id)
                owner_name = user.name or user.username if user else None
        return OpenApiAppResponse(
            id=e.id,
            app_id=e.app_id,
            name=e.name,
            description=e.description,
            scopes=parse_scopes(e.scopes),
            status=e.status,
            auth_mode=e.auth_mode,
            rate_limit_per_minute=e.rate_limit_per_minute,
            owner_type=e.owner_type,
            owner_id=e.owner_id,
            owner_name=owner_name,
            approved=e.approved,
            last_used_at=e.last_used_at,
            created_at=e.created_at,
        )
