#!/usr/bin/env python3
"""开放平台应用业务逻辑。

包含两部分：
1. 管理员侧的应用 CRUD、密钥生成与重置（OpenApiAppService）；
2. 开放平台协议相关的私有函数：AppId 生成规则、签名串拼装、scope 解析。

通用加密原语（SHA256、Fernet、HMAC）在 src/utils/security.py。
"""

from __future__ import annotations

import secrets
from time import time
from typing import Any
from urllib.parse import urlencode, urlparse

from fastapi import Request

from src.core.config import settings
from src.core.exceptions import AuthenticationException, NotFoundException
from src.core.logger import logger
from src.constants.constants import (
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_NONCE,
    OPENAPI_HEADER_SIGNATURE,
    OPENAPI_HEADER_TIMESTAMP,
)
from src.constants.enums import AppAuthMode
from src.utils.security import generate_secret_key
from src.models.entities.app_entity import OpenApiAppEntity
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.openapi_app import CurrentApp, OpenApiAppResponse
from src.utils import security

# ── 开放平台鉴权协议常量 ─────────────────────────────────
HMAC_TIMESTAMP_WINDOW_SECONDS = 300


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
# 开放平台协议：签名串拼装
# ============================================================

def _sorted_query(query_string: str) -> str:
    """把 query string 按 key 字典序规范化回 k=v&k=v。"""
    if not query_string:
        return ""
    pairs: list[tuple[str, str]] = []
    for kv in query_string.split("&"):
        if not kv:
            continue
        if "=" in kv:
            k, v = kv.split("=", 1)
        else:
            k, v = kv, ""
        pairs.append((k, v))
    pairs.sort(key=lambda x: x[0])
    return urlencode(pairs, doseq=True)


def build_signing_string(method: str, url: str, body: bytes, timestamp: str, nonce: str) -> str:
    """构造 HMAC 待签名串（与外部调用方的协议约定，勿随意改）。

    格式：METHOD\\nPATH\\nSortedQuery\\nSHA256(body)\\nTimestamp\\nNonce
    """
    parsed = urlparse(url)
    body_hash = security.sha256_hex(body.decode("utf-8")) if body else ""
    return "\n".join([
        method.upper(),
        parsed.path or "/",
        _sorted_query(parsed.query),
        body_hash,
        timestamp,
        nonce,
    ])


def verify_request_signature(
    *,
    app_key_plain: str,
    method: str,
    url: str,
    body: bytes,
    timestamp: str,
    nonce: str,
    signature: str,
) -> bool:
    """校验请求 HMAC 签名。"""
    expected = security.hmac_sha256_hex(
        app_key_plain,
        build_signing_string(method, url, body, timestamp, nonce),
    )
    return security.constant_time_equals(expected, signature or "")


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

class OpenApiAppService:
    """开放应用管理。"""

    def __init__(self, repo: OpenApiAppRepository) -> None:
        self._repo = repo

    # ── 鉴权（每请求调用）──────────────────────────────
    async def authenticate(self, request: Request) -> CurrentApp:
        """解析开放平台应用身份（X-App-Id / X-App-Key 或 HMAC 签名头）。

        鉴权逻辑按 app.auth_mode 分流：
            - plain：仅接受 X-App-Key 明文比对 SHA256；
            - hmac：  仅接受 HMAC 签名（时间窗 + nonce 去重 + 重算签名）；
            - both：  两种都接受（灰度期）。
        """
        app_id = request.headers.get(OPENAPI_HEADER_APP_ID)
        if not app_id:
            raise AuthenticationException(message="缺少请求头 X-App-Id")

        app = self._repo.get_by_app_id(app_id)
        if app is None or app.status != "active":
            raise AuthenticationException(message="App 无效或已停用")

        try:
            mode = AppAuthMode(app.auth_mode or AppAuthMode.PLAIN.value)
        except ValueError:
            mode = AppAuthMode.PLAIN

        plain_key = request.headers.get(OPENAPI_HEADER_APP_KEY)
        signature = request.headers.get(OPENAPI_HEADER_SIGNATURE)
        timestamp = request.headers.get(OPENAPI_HEADER_TIMESTAMP, "")
        nonce = request.headers.get(OPENAPI_HEADER_NONCE, "")

        authenticated = False

        # 分支 1：明文 AppKey 校验
        if mode in (AppAuthMode.PLAIN, AppAuthMode.BOTH) and plain_key:
            authenticated = security.constant_time_equals(
                security.sha256_hex(plain_key), app.app_key_hash
            )

        # 分支 2：HMAC 签名校验
        if (
            not authenticated
            and mode in (AppAuthMode.HMAC, AppAuthMode.BOTH)
            and signature
        ):
            authenticated = await self._verify_hmac_signature(
                request=request,
                app_encrypted=app.app_key_encrypted,
                timestamp=timestamp,
                nonce=nonce,
                signature=signature,
            )

        if not authenticated:
            raise AuthenticationException(message="应用鉴权失败")

        # 更新 last_used_at（失败不阻断主流程）
        try:
            self._repo.touch_last_used(app_id)
        except Exception:
            self._repo.session.rollback()

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
        timestamp: str,
        nonce: str,
        signature: str,
    ) -> bool:
        """HMAC 签名校验：时间窗 + 解密 secret + 重算签名 + nonce 去重。"""
        # 1. 时间窗
        try:
            ts = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(time() - ts) > HMAC_TIMESTAMP_WINDOW_SECONDS:
            return False

        # 2. 解密取回明文 secret
        secret = security.decrypt_text(app_encrypted)
        if not secret:
            return False

        # 3. 重算签名
        body = b""
        try:
            body = await request.body()
        except Exception:
            body = b""

        if not verify_request_signature(
            app_key_plain=secret,
            method=request.method,
            url=str(request.url),
            body=body,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        ):
            return False

        # 4. nonce 去重（TODO: 接 Redis SETNX）
        return True

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
        # 极小概率碰撞，重生成一次
        while self._repo.get_by_app_id(app_id) is not None:
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
        created = self._repo.create(entity)
        logger.info(f"OpenAPI app created: app_id={app_id} name={name} owner={owner_user_id}")
        return self._to_response(created), app_key_plain

    # ── 查询 ────────────────────────────────────────────
    def list_apps(self, keyword: str | None = None, limit: int = 100) -> list[OpenApiAppResponse]:
        stmt = self._repo._base_query()
        if keyword:
            stmt = stmt.where(OpenApiAppEntity.name.like(f"%{keyword}%"))
        rows = list(self._repo.session.execute(stmt.limit(limit)).scalars().all())
        return [self._to_response(r) for r in rows]

    def get_app(self, id: int) -> OpenApiAppResponse:
        e = self._repo.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        return self._to_response(e)

    # ── 更新 ────────────────────────────────────────────
    def update_app(self, id: int, patch: dict[str, Any]) -> OpenApiAppResponse:
        e = self._repo.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        if "scopes" in patch and patch["scopes"] is not None:
            e.scopes = ",".join(patch["scopes"])
            patch.pop("scopes")
        for k, v in patch.items():
            if v is not None and hasattr(e, k):
                setattr(e, k, v)
        self._repo.session.flush()
        return self._to_response(e)

    # ── 重置 AppKey（轮换）────────────────────────────
    def rotate_key(self, id: int) -> tuple[OpenApiAppResponse, str]:
        """重置 AppKey：旧 key 立即失效，返回新明文（仅一次）。"""
        e = self._repo.get_by_id(id)
        if e is None:
            raise NotFoundException(message=f"应用 {id} 不存在")
        new_plain = generate_secret_key()
        e.app_key_hash = security.sha256_hex(new_plain)
        e.app_key_encrypted = security.encrypt_text(new_plain)
        self._repo.session.flush()
        logger.info(f"OpenAPI app key rotated: app_id={e.app_id}")
        return self._to_response(e), new_plain

    # ── 删除 ────────────────────────────────────────────
    def delete_app(self, id: int) -> bool:
        return self._repo.soft_delete(id)

    # ── 内部用：entity → DTO ───────────────────────────
    @staticmethod
    def _to_response(e: OpenApiAppEntity) -> OpenApiAppResponse:
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
