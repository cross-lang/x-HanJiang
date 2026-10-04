#!/usr/bin/env python3
"""开放平台开发者应用业务逻辑（开发者门户视角）。

与管理端 OpenApiAppService 的关系：
- 数据同一张 openapi_apps 表，归属用 owner_type/owner_id 区分；
- 本服务所有查询/操作强制 owner_type='developer' AND owner_id=当前开发者，
  天然实现"开发者只看并只能操作自己的应用"的数据隔离；
- 创建/重置密钥复用协议级公共函数（generate_app_id/parse_scopes），
  不反向依赖管理端服务（域隔离）。
"""

from __future__ import annotations

from src.constants.enums import (
    AppApprovalStatus,
    AppOwnerType,
    AppStatus,
    NotificationChannel,
    NotificationEvent,
    StationMessageStatus,
)
from src.core.exceptions import NotFoundException
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.notification_entity import NotificationRecordEntity
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.open_portal.app import (
    OpenAppResponse,
)
from src.utils import security
from src.utils.openapi_utils import build_scope_dict_list, generate_app_id, parse_scopes

# 开放应用审批权限码（管理端 openapi_app.py 的 update_app_approval 依赖此权限）
_APPROVAL_PERM_CODE = "openapi_app:scopes"


class DeveloperOpenAppService:
    """开发者门户应用管理。"""

    def __init__(self, repo: OpenApiAppRepository) -> None:
        self._repository = repo

    # ── 创建 ────────────────────────────────────────────

    def create_app(
        self,
        *,
        developer_id: int,
        name: str,
        description: str,
        scopes: list[str],
        auth_mode: str,
    ) -> tuple[OpenAppResponse, str]:
        """开发者创建应用。

        创建即申请：scopes 直接落到应用上但审批状态为 pending，
        管理员审批通过后才对外生效（网关侧已强制拦截：审批未通过时
        OpenGatewayService.authenticate 一律拒绝，见 services/open/gateway_service.py）。

        Returns:
            (响应 DTO, 明文 AppKey)。明文仅此一次返回（由 API 层组装进响应）。
        """
        app_id = generate_app_id()
        while self._repository.get_by_app_id(app_id) is not None:
            app_id = generate_app_id()
        app_key_plain = security.generate_secret_key()
        entity = OpenApiAppEntity(
            app_id=app_id,
            app_key_hash=security.sha256_hex(app_key_plain),
            app_key_encrypted=security.encrypt_text(app_key_plain),
            name=name,
            description=description,
            scopes=",".join(scopes),
            auth_mode=auth_mode,
            owner_type=AppOwnerType.DEVELOPER.value,
            owner_id=developer_id,
            approval_status=AppApprovalStatus.PENDING.value,
            status=AppStatus.ACTIVE.value,
        )
        created = self._repository.create(entity)
        self._repository.commit()
        self._notify_approvers(created, developer_id)
        return self._to_response(created), app_key_plain

    def _notify_approvers(self, app: OpenApiAppEntity, developer_id: int) -> None:
        """通知拥有审批权限的管理系统用户：新的应用申请待审批（管理端站内信）。

        收件人为拥有 openapi_app:scopes 权限的管理员；站内信随本服务同会话提交，
        标题约定含「审批」关键词，管理端站内信点击后跳转应用管理页。
        """
        try:
            approver_ids = self._repository.list_user_ids_by_perm(_APPROVAL_PERM_CODE)
            if not approver_ids:
                return
            dev = self._repository.get_owner_developer(developer_id)
            dev_name = f"{dev.name or dev.username}" if dev else f"开发者#{developer_id}"
            scopes_text = parse_scopes(app.scopes)
            title = "【开放平台】新的应用申请待审批"
            content = (
                f"开发者 {dev_name} 提交了应用申请「{app.name}」（App ID：{app.app_id}），"
                f"申请权限：{scopes_text or '无'}。请前往「开放平台 → 应用管理」审批。"
            )
            for uid in approver_ids:
                self._repository.session.add(
                    NotificationRecordEntity(
                        event_type=NotificationEvent.OPENAPI_APP_CREATED.mark,
                        channel=NotificationChannel.STATION.value,
                        recipient=f"user:{uid}",
                        subject=title,
                        content=content,
                        status=StationMessageStatus.UNREAD.value,
                        retry_count=0,
                        max_retries=0,
                    )
                )
            self._repository.commit()
        except Exception:
            # 通知失败不影响应用创建主流程
            self._repository.session.rollback()

    # ── 查询 ────────────────────────────────────────────

    def list_apps(
        self,
        *,
        developer_id: int,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        """分页查询当前开发者的应用（owner 隔离）。"""
        skip = (page - 1) * page_size
        rows, total = self._repository.search_by_keyword(
            keyword=keyword,
            owner_type=AppOwnerType.DEVELOPER.value,
            owner_id=developer_id,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_response(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_app(self, app_id: int, developer_id: int) -> OpenAppResponse:
        """查询应用详情（仅限本人名下，否则 404 不暴露存在性）。"""
        return self._to_response(self._require_owned(app_id, developer_id))

    def list_scopes(self) -> list[dict[str, object]]:
        """查询全部可用（未废弃）的开放平台 scope，供开发者创建应用/申请权限时勾选。

        scope 元数据唯一来源为 constants/scopes.py 启动时对账的 openapi_scopes 表，
        与管理端共享 repository 与公共映射函数（build_scope_dict_list）。
        """
        entities = self._repository.list_active_scopes()
        return build_scope_dict_list(entities)

    # ── 更新 ────────────────────────────────────────────

    def update_app(
        self,
        app_id: int,
        developer_id: int,
        patch: dict[str, object],
    ) -> OpenAppResponse:
        """更新应用基本信息（name/description/auth_mode，不含 scopes/status）。"""
        e = self._require_owned(app_id, developer_id)
        for k, v in patch.items():
            if v is not None and hasattr(e, k):
                setattr(e, k, v)
        self._repository.commit()
        return self._to_response(e)

    def apply_scopes(
        self,
        app_id: int,
        developer_id: int,
        scopes: list[str],
        reason: str | None,
    ) -> OpenAppResponse:
        """提交 scope 申请/调整：更新目标 scopes 并置审批状态为 pending。

        审批动作（通过/驳回）由管理系统管理员执行（admin/v1 的 scopes 与 approval 端点），
        通过后 approval_status=approved、驳回后保留 pending 待开发者调整重提。
        """
        e = self._require_owned(app_id, developer_id)
        e.scopes = ",".join(scopes)
        e.approval_status = AppApprovalStatus.PENDING.value
        e.approval_note = None
        e.scope_apply_reason = (reason or "").strip() or None
        self._repository.commit()
        return self._to_response(e)

    # ── 重置密钥 ────────────────────────────────────────

    def rotate_key(self, app_id: int, developer_id: int) -> tuple[OpenAppResponse, str]:
        """重置 AppKey：旧 key 立即失效，返回新明文（仅一次）。"""
        e = self._require_owned(app_id, developer_id)
        new_plain = security.generate_secret_key()
        e.app_key_hash = security.sha256_hex(new_plain)
        e.app_key_encrypted = security.encrypt_text(new_plain)
        self._repository.commit()
        return self._to_response(e), new_plain

    # ── 删除 ────────────────────────────────────────────

    def delete_app(self, app_id: int, developer_id: int) -> bool:
        """软删除应用（仅限本人名下）。"""
        self._require_owned(app_id, developer_id)
        self._repository.soft_delete(app_id)
        self._repository.commit()
        return True

    # ── 内部工具 ────────────────────────────────────────

    def _require_owned(self, app_id: int, developer_id: int) -> OpenApiAppEntity:
        """按 ID 取应用并校验归属当前开发者；不满足按 404 处理（不暴露存在性）。"""
        e = self._repository.get_by_id(app_id)
        if e is None or e.owner_type != AppOwnerType.DEVELOPER.value or e.owner_id != developer_id:
            raise NotFoundException(message=f"应用 {app_id} 不存在")
        return e

    def _to_response(self, e: OpenApiAppEntity) -> OpenAppResponse:
        return OpenAppResponse(
            id=e.id,
            app_id=e.app_id,
            name=e.name,
            description=e.description,
            scopes=parse_scopes(e.scopes),
            auth_mode=e.auth_mode,
            status=e.status,
            owner_type=e.owner_type,
            owner_id=e.owner_id,
            approval_status=e.approval_status,
            approval_note=e.approval_note,
            last_used_at=e.last_used_at,
            created_at=e.created_at,
        )
