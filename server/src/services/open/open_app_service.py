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

from src.constants.enums import AppApprovalStatus, AppOwnerType, AppStatus
from src.core.exceptions import NotFoundException
from src.models.entities.app_entity import OpenApiAppEntity
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.open.app import (
    OpenAppResponse,
)
from src.utils import security
from src.utils.openapi_utils import generate_app_id, parse_scopes


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
        管理员审批通过后才对外生效语义（网关鉴权不校验审批态，
        审批未通过时建议网关侧拦截——见 OpenApiAppService.authenticate 备注）。

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
        return self._to_response(created), app_key_plain

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
