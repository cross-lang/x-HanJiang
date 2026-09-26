#!/usr/bin/env python3
"""开放平台应用业务逻辑。

包含两部分：
1. 管理员侧的应用 CRUD、密钥生成与重置（OpenApiAppService）；
2. 开放平台协议相关的私有函数：AppId 生成规则、签名串拼装、scope 解析。

通用加密原语（SHA256、Fernet、HMAC）在 src/utils/security.py。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from fastapi import Request

from src.core.config import settings
from src.core.exceptions import AuthenticationException, NotFoundException
from src.core.logger import logger
from src.constants.constants import (
    OPENAPI_ALGORITHM,
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_AUTHORIZATION,
    OPENAPI_HEADER_DATE,
    OPENAPI_SIGNATURE_WINDOW_SECONDS,
)
from src.constants.enums import AppAuthMode
from src.utils.security import generate_secret_key
from src.models.entities.app_entity import OpenApiAppEntity
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.openapi_app import CurrentApp, OpenApiAppResponse
from src.services.base_service import BaseService
from src.utils import security

# ── 开放平台鉴权协议常量 ─────────────────────────────────


# ============================================================
# 开放平台协议：AppId 生成
# ============================================================

def generate_app_id() -> str:
    """生成对外 AppId。

    前缀 = 项目缩写 hj + 环境标识：
        - 生产环境：hj_live_xxxxxxxx
        - 其他环境：hj_test_xxxxxxxx
    主体 16 字节随机 → 32 hex 字符，约 128bit 熵，抗枚举。
    """
    env_prefix = "hj_live_" if settings.is_production else "hj_test_"
    return f"{env_prefix}{secrets.token_hex(16)}"


# ============================================================
# 开放平台协议：HanJiang-1 签名串拼装（参考 WPS-4 风格）
# ============================================================

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
    直接拼接，无分隔符（参考 WPS-4）。
    """
    body_hash = security.sha256_hex(body.decode("utf-8")) if body else ""
    return "".join([
        OPENAPI_ALGORITHM,
        method.upper(),
        uri,
        content_type,
        date,
        body_hash,
    ])


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
        build_signing_string(
            method=method, uri=uri, content_type=content_type, date=date, body=body
        ),
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
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


# ============================================================
# scope 解析
# ============================================================

def parse_scopes(scopes: str | None) -> list[str]:
    """库中逗号分隔的 scopes 字段 → list[str]，去空。"""
    if not scopes:
        return []
    return [s.strip() for s in scopes.split(",") if s.strip()]


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

        鉴权逻辑按 app.auth_mode 分流：
            - plain：仅接受 X-App-Key 明文比对 SHA256；
            - hmac：  仅接受 HanJiang-1 签名（时间窗 + 重算签名）；
            - both：  两种都接受（灰度期）。
        """
        app_id = request.headers.get(OPENAPI_HEADER_APP_ID)
        if not app_id:
            raise AuthenticationException(message="缺少请求头 X-App-Id")

        app = self._repository.get_by_app_id(app_id)
        if app is None or app.status != "active":
            raise AuthenticationException(message="App 无效或已停用")

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
            authenticated = security.constant_time_equals(
                security.sha256_hex(plain_key), app.app_key_hash
            )

        # 分支 2：HanJiang-1 签名校验
        if (
            not authenticated
            and mode in (AppAuthMode.HMAC, AppAuthMode.BOTH)
            and authorization
        ):
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
            self._repository.session.rollback()

        return CurrentApp(
            app_id=app.app_id,
            name=app.name,
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
        now = datetime.now(timezone.utc)
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

        # 5. Content-Type
        content_type = request.headers.get("content-type", "")

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
    def create_app(
        self,
        *,
        name: str,
        scopes: list[str],
        rate_limit_per_minute: int,
        auth_mode: str,
        owner_user_id: int | None,
    ) -> tuple[OpenApiAppResponse, str]:
        """新建应用，返回 (DTO, 明文 AppKey)。明文 AppKey 仅此次返回。"""
        app_id = generate_app_id()
        while self._repository.get_by_app_id(app_id) is not None:
            app_id = generate_app_id()

        app_key_plain = generate_secret_key()
        entity = OpenApiAppEntity(
            app_id=app_id,
            app_key_hash=security.sha256_hex(app_key_plain),
            app_key_encrypted=security.encrypt_text(app_key_plain),
            name=name,
            scopes=",".join(scopes),
            rate_limit_per_minute=rate_limit_per_minute,
            auth_mode=auth_mode,
            owner_user_id=owner_user_id,
            status="active",
        )
        created = self._repository.create(entity)
        self._commit()
        self._log_action("created", created.id, app_id=app_id, name=name)
        return self._to_response(created), app_key_plain

    # ── 查询 ────────────────────────────────────────────
    def list_apps(self, keyword: str | None = None, limit: int = 100) -> list[OpenApiAppResponse]:
        stmt = self._repository._base_query()
        if keyword:
            stmt = stmt.where(OpenApiAppEntity.name.like(f"%{keyword}%"))
        rows = list(self._repository.session.execute(stmt.limit(limit)).scalars().all())
        return [self._to_response(r) for r in rows]

    def get_by_id(self, id: int) -> OpenApiAppResponse:
        """根据 ID 查询应用详情，不存在抛 NotFound。"""
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        return self._to_response(e)

    # ── 更新 ────────────────────────────────────────────
    def update(self, id: int, patch: dict[str, Any]) -> OpenApiAppResponse:
        e = self._repository.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        if "scopes" in patch and patch["scopes"] is not None:
            e.scopes = ",".join(patch["scopes"])
            patch.pop("scopes")
        for k, v in patch.items():
            if v is not None and hasattr(e, k):
                setattr(e, k, v)
        self._repository.session.flush()
        self._commit()
        self._log_action("updated", id)
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
        self._repository.session.flush()
        self._commit()
        self._log_action("key rotated", id, app_id=e.app_id)
        return self._to_response(e), new_plain

    # ── 删除 ────────────────────────────────────────────
    def delete(self, id: int) -> bool:
        ok = self._repository.soft_delete(id)
        self._commit()
        self._log_action("deleted", id)
        return ok

    # ── Entity → DTO ────────────────────────────────────
    def _to_response(self, e: OpenApiAppEntity) -> OpenApiAppResponse:
        return OpenApiAppResponse(
            id=e.id,
            app_id=e.app_id,
            name=e.name,
            scopes=parse_scopes(e.scopes),
            status=e.status,
            auth_mode=e.auth_mode,
            rate_limit_per_minute=e.rate_limit_per_minute,
            owner_user_id=e.owner_user_id,
            last_used_at=e.last_used_at,
            created_at=e.created_at,
        )
