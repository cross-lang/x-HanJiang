#!/usr/bin/env python3
"""
令牌管理模块

基于 PyJWT 实现访问/刷新令牌的签发与校验。

Functions:
    create_access_token: 签发访问令牌
    create_refresh_token: 签发刷新令牌
    decode_token: 解码并校验令牌
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from src.core.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """签发 JWT 令牌。

    Args:
        subject: 主体标识（用户ID字符串）
        token_type: 令牌类型（access/refresh）
        expires_delta: 有效时长
        extra_claims: 额外声明（如 username）

    Returns:
        str: 编码后的 JWT 字符串
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": f"{now.timestamp():.0f}-{token_type}",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )


def create_access_token(user_id: int, extra_claims: dict[str, Any] | None = None) -> str:
    """签发访问令牌。

    Args:
        user_id: 用户ID
        extra_claims: 额外声明

    Returns:
        str: 访问令牌
    """
    return _create_token(
        subject=str(user_id),
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.auth.access_token_expire_minutes),
        extra_claims=extra_claims,
    )


def create_refresh_token(user_id: int, extra_claims: dict[str, Any] | None = None) -> str:
    """签发刷新令牌。

    Args:
        user_id: 用户ID
        extra_claims: 额外声明

    Returns:
        str: 刷新令牌
    """
    return _create_token(
        subject=str(user_id),
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.auth.refresh_token_expire_days),
        extra_claims=extra_claims,
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """解码并校验 JWT 令牌。

    Args:
        token: JWT 字符串
        expected_type: 期望的令牌类型（access/refresh），None 表示不校验类型

    Returns:
        dict[str, Any]: 解码后的声明字典

    Raises:
        jwt.ExpiredSignatureError: 令牌过期
        jwt.InvalidTokenError: 令牌无效
        ValueError: 令牌类型不匹配
    """
    payload = jwt.decode(
        token,
        settings.auth.secret_key,
        algorithms=[settings.auth.algorithm],
        # aud 声明仅用于标记 client_type（console 等），非标准 audience 校验需求，
        # 故禁用 PyJWT 的自动 audience 校验，避免 InvalidAudienceError
        options={"verify_aud": False},
    )
    if expected_type and payload.get("type") != expected_type:
        raise ValueError(f"令牌类型不匹配: 期望 {expected_type}, 实际 {payload.get('type')}")
    return payload
