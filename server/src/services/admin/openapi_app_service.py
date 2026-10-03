#!/usr/bin/env python3
"""开放平台应用业务逻辑。
包含两部分：
1. 管理员侧的应用 CRUD、密钥生成与重置（OpenApiAppService）；
2. 开放平台协议相关的私有函数：签名串拼装、HMAC 校验（通用函数 generate_app_id /
   parse_scopes / scope 目录映射已抽至 src/utils/openapi_utils.py，此处 re-export 保持旧引用兼容）。
通用加密原语（SHA256、Fernet、HMAC）在 src/utils/security.py。
"""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from fastapi import Request

from src.constants.constants import (
    OPENAPI_ALGORITHM,
    OPENAPI_CONTENT_TYPE,
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_AUTHORIZATION,
    OPENAPI_HEADER_DATE,
    OPENAPI_SIGNATURE_WINDOW_SECONDS,
)
from src.constants.enums import AppApprovalStatus, AppAuthMode, AppOwnerType, AppStatus, NotificationEvent
from src.constants.permissions import PermissionAction
from src.core.exceptions import AuthenticationException, AuthorizationException, NotFoundException
from src.models.entities.app_entity import OpenApiAppEntity
from src.notification.decorators import notify
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.openapi_app import CurrentApp, OpenApiAppResponse
from src.services.admin.base_service import BaseService, audit_crud
from src.utils import security
from src.utils.openapi_utils import build_scope_dict_list, generate_app_id, parse_scopes
from src.utils.security import generate_secret_key


def build_signing_string(
    *,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
) -> str:
    """构造 HanJiang-1 待签名串（与外部调用方的协议约定，勿随意改）。
    格式：Ver + METHOD + URI + Content-Type + Date + SHA256(body)
    直接拼接，无分隔符。
    注意：Content-Type 固定为 application/json（与请求是否携带 body 无关），
    GET 无 body 时同样拼接该固定值，body 为空则 SHA256(body) 取空字符串。
    """
    body_hash = security.sha256_hex(body.decode("utf-8")) if body else ""
    return "".join(
        [
            OPENAPI_ALGORITHM,
            method.upper(),
            uri,
            content_type,
            date,
            body_hash,
        ]
    )


def verify_request_signature(
    *,
    app_key_plain: str,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
    signature: str,
) -> bool:
    """校验请求签名。"""
    expected = security.hmac_sha256_hex(
        app_key_plain,
        build_signing_string(method=method, uri=uri, content_type=content_type, date=date, body=body),
    )
    return security.constant_time_equals(expected, signature)


def _extract_uri(request: Request) -> str:
    """从请求中提取 URI（path + raw query，不含域名）。"""
    uri = request.url.path
    if request.url.query:
        uri += f"?{request.url.query}"
    return uri


def _parse_http_date(date_str: str) -> datetime | None:
    """解析 HTTP 标准格式日期，如 'Wed, 23 Jan 2013 06:43:08 GMT'。"""
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (TypeError, ValueError):
        return None


# ============================================================

# scope 解析（公共函数已抽至 src/utils/openapi_utils.py，此处 re-export 保持旧引用兼容）

# ============================================================


# ============================================================

# 管理员侧 CRUD

# ============================================================


class OpenApiAppService(BaseService[OpenApiAppResponse, int, OpenApiAppRepository]):
    """开放应用管理。"""

    entity_type = "openapi_app"

    def __init__(self, repo: OpenApiAppRepository) -> None:
        self._repository = repo

    # ── 鉴权（每请求调用）──────────────────────────────

    async def authenticate(self, request: Request) -> CurrentApp:
        """解析开放平台应用身份。
        鉴权流程：
            1. 应用存在且启用（status=active）；
            2. 审批状态须为 approved（pending/rejected 一律拒绝——申请-审批闭环的强制门槛）；
            3. 按 app.auth_mode 分流：
               - plain：仅接受 X-App-Key 明文比对 SHA256；
               - hmac：  仅接受 HanJiang-1 签名（时间窗 + 重算签名）；
               - both：  两种都接受（灰度期）。
        """
        app_id = request.headers.get(OPENAPI_HEADER_APP_ID)
        if not app_id:
            raise AuthenticationException(message="缺少请求头 X-App-Id")
        app = self._repository.get_by_app_id(app_id)
        if app is None or app.status != AppStatus.ACTIVE.value:
            raise AuthenticationException(message="App 无效或已停用")
        # 审批门槛：仅放行已通过审批的应用（开发者自助应用需管理端审批通过后方可调用）
        if app.approval_status != AppApprovalStatus.APPROVED.value:
            raise AuthorizationException(
                message=f"应用 {app.app_id} 未通过审批（当前状态：{app.approval_status}），请联系管理员"
            )
        try:
            mode = AppAuthMode(app.auth_mode or AppAuthMode.PLAIN.value)
        except ValueError:
            mode = AppAuthMode.PLAIN
        plain_key = request.headers.get(OPENAPI_HEADER_APP_KEY)
        authorization = request.headers.get(OPENAPI_HEADER_AUTHORIZATION, "")
        date = request.headers.get(OPENAPI_HEADER_DATE, "")
        authenticated = False
        # 分支 1：明文 AppKey 校验
        if mode in (AppAuthMode.PLAIN, AppAuthMode.BOTH) and plain_key:
            authenticated = security.constant_time_equals(security.sha256_hex(plain_key), app.app_key_hash)
        # 分支 2：HanJiang-1 签名校验
        if not authenticated and mode in (AppAuthMode.HMAC, AppAuthMode.BOTH) and authorization:
            authenticated = await self._verify_hmac_signature(
                request=request,
                app_encrypted=app.app_key_encrypted,
                date=date,
                authorization=authorization,
            )
        if not authenticated:
            raise AuthenticationException(message="应用鉴权失败")
        # 更新 last_used_at（失败不阻断主流程）
        try:
            self._repository.touch_last_used(app_id)
        except Exception:
            self._repository.rollback()
        return CurrentApp(
            app_id=app.app_id,
            name=app.name,
            description=app.description,
            scopes=parse_scopes(app.scopes),
            auth_mode=mode.value,
            rate_limit_per_minute=app.rate_limit_per_minute,
        )

    async def _verify_hmac_signature(
        self,
        *,
        request: Request,
        app_encrypted: str | None,
        date: str,
        authorization: str,
    ) -> bool:
        """HanJiang-1 签名校验：时间窗 + 解密 secret + 重算签名。"""
        # 1. 时间窗：解析 HTTP Date 格式
        if not date:
            return False
        request_time = _parse_http_date(date)
        if request_time is None:
            return False
        now = datetime.now(UTC)
        if abs((now - request_time).total_seconds()) > OPENAPI_SIGNATURE_WINDOW_SECONDS:
            return False
        # 2. 解密取回明文 secret
        secret = security.decrypt_text(app_encrypted)
        if not secret:
            return False
        # 3. 提取 Authorization 中的签名值
        # 格式：HanJiang-1 {app_id}:{signature}
        parts = authorization.split(":", 1)
        if len(parts) != 2 or not parts[1]:
            return False
        signature = parts[1].strip()
        # 4. 取请求体
        body = b""
        try:
            body = await request.body()
        except Exception:
            body = b""
        # 5. Content-Type（协议固定为 application/json，不从请求头取值）
        content_type = OPENAPI_CONTENT_TYPE
        # 6. 重算签名并比对
        return verify_request_signature(
            app_key_plain=secret,
            method=request.method,
            uri=_extract_uri(request),
            content_type=content_type,
            date=date,
            body=body,
            signature=signature,
        )

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
        """
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
            approval_status=AppApprovalStatus.APPROVED.value,
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
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """分页查询应用列表（不含已软删除）。

        Args:
            keyword: 按名称模糊搜索
            owner_type: 按归属类型过滤（developer 开发者自助 / admin 管理员分配）

        Returns:
            {items, total, page, page_size}，与用户列表等接口分页口径一致。
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.search_by_keyword(
            keyword=keyword,
            owner_type=owner_type,
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

    @notify(
        NotificationEvent.OPENAPI_APP_UPDATED,
        target="owner",
        vars_extractor=lambda r: {"app_name": r.name, "app_id": r.app_id},
    )
    @audit_crud(PermissionAction.EDIT.mark)
    def update(self, id: int, patch: dict[str, Any], operator: dict[str, Any] | None = None) -> OpenApiAppResponse:
        """更新应用基本信息（不含 scopes / status，走专用方法）。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        for k, v in patch.items():
            if v is not None and hasattr(e, k):
                setattr(e, k, v)
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    @notify(
        NotificationEvent.OPENAPI_APP_UPDATED,
        target="owner",
        vars_extractor=lambda r: {"app_name": r.name, "app_id": r.app_id},
    )
    @audit_crud(PermissionAction.SCOPES.mark)
    def update_scopes(self, id: int, scopes: list[str], operator: dict[str, Any] | None = None) -> OpenApiAppResponse:
        """覆盖更新应用 scope 列表（管理端授权操作，视为审批通过：置 approval_status=approved）。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        e.scopes = ",".join(scopes)
        e.approval_status = AppApprovalStatus.APPROVED.value
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    def update_approval(
        self,
        id: int,
        *,
        approved: bool,
        note: str | None = None,
        operator: dict[str, Any] | None = None,
    ) -> OpenApiAppResponse:
        """管理端审批开发者 scope 申请：通过（approved）或驳回（rejected）+ 审批意见。

        通过仅置状态（scope 本身由开发者申请端点已写入目标值）；
        驳回保留 pending 的 scopes 原值并记录驳回原因。
        """
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        e.approval_status = (
            AppApprovalStatus.APPROVED.value if approved else AppApprovalStatus.REJECTED.value
        )
        e.approval_note = (note or "").strip() or None
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    @notify(
        NotificationEvent.OPENAPI_APP_UPDATED,
        target="owner",
        vars_extractor=lambda r: {"app_name": r.name, "app_id": r.app_id},
    )
    @audit_crud(PermissionAction.STATUS.mark)
    def update_status(self, id: int, status: str, operator: dict[str, Any] | None = None) -> OpenApiAppResponse:
        """启用或禁用应用。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        e.status = status
        self._repository.flush()
        self._commit()
        return self._to_response(e)

    # ── 重置 AppKey（轮换）────────────────────────────

    def rotate_key(self, id: int) -> tuple[OpenApiAppResponse, str]:
        """重置 AppKey：旧 key 立即失效，返回新明文（仅一次）。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
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
        ok = self._repository.soft_delete(id)
        self._commit()
        return ok

    # ── Entity → DTO ────────────────────────────────────

    def _to_response(self, e: OpenApiAppEntity) -> OpenApiAppResponse:
        owner_name = None
        if e.owner_id is not None:
            if e.owner_type == AppOwnerType.DEVELOPER.value:
                owner = self._repository.get_owner_developer(e.owner_id)
                owner_name = owner.name or owner.username if owner else None
            else:
                owner = self._repository.get_owner_user(e.owner_id)
                owner_name = owner.name or owner.username if owner else None
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
            owner_user_id=e.owner_user_id,
            owner_name=owner_name,
            approval_status=e.approval_status,
            approval_note=e.approval_note,
            last_used_at=e.last_used_at,
            created_at=e.created_at,
        )
