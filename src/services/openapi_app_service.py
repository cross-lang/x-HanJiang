#!/usr/bin/env python3
"""开放平台应用业务逻辑。

包含两部分：
1. 管理员侧的应用 CRUD、密钥生成与重置（OpenApiAppService）；
2. 开放平台协议相关的私有函数：AppId 生成规则、签名串拼装、scope 解析。

通用加密原语（SHA256、Fernet、HMAC）在 src/utils/security.py。
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode, urlparse

from src.core.config import settings
from src.core.exceptions import NotFoundException
from src.core.logger import logger
from src.utils.security import generate_secret_key
from src.models.entities.app_entity import OpenApiAppEntity
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.openapi_app import OpenApiAppResponse
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
