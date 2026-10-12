#!/usr/bin/env python3
"""登录密码加密编排（方案 B：RSA-OAEP + nonce 防重放）。

职责边界：
- 位于 service.login 之前：先解出明文密码，再走原有认证链路。
- 密码传输链路：前端取公钥 → 加密 `nonce|timestamp|password` → POST /auth/login
  {encrypted_password, nonce} → 本模块解密校验 → 返回明文密码交给 service。
- 所有解密类失败统一抛 AuthenticationException（与登录失败同文案），
  不向调用方暴露 nonce 是否有效 / 时间戳是否越界等内部细节，避免探测。

开关：AUTH_ENCRYPTION_ENABLED=false 时直通（本地 curl 联调用，生产默认开启）。

RSA 算法原语位于 utils/security.py（rsa_public_key_pem / rsa_decrypt），
本模块只承载"登录场景"的编排规则（nonce 一次性 / 时间窗 / 结构校验）。
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from src.core.config import settings
from src.core.exceptions import AuthenticationException
from src.core.logger import logger
from src.utils.security import rsa_decrypt

if TYPE_CHECKING:
    from src.infras.cache import CacheProvider

#: nonce 键前缀与有效期（秒）。nonce 在签发时预写、登录消费时原子删除，
#: 过期后重放同一 nonce 会因键不存在而被拒绝。
_NONCE_PREFIX = "auth:nonce:"
_NONCE_TTL = 300

#: 密文时间戳允许偏差（秒）。前端使用公钥接口下发的服务器时间戳原样拼接，
#: 因此该窗口只需容忍网络/处理延迟，无需容忍客户端时钟漂移。
_TS_TOLERANCE_SECONDS = 300

#: 失败统一文案（与 service 登录失败一致，防账号探测与细节泄露）
_INVALID_CREDENTIALS = "用户名或密码错误"


def issue_login_nonce(cache: CacheProvider) -> str:
    """签发一次性 nonce 并预写缓存（TTL 300s）。

    返回的 nonce 随公钥接口下发给前端，前端原样拼进密文；
    登录时通过 getdel 原子消费，第二次使用同一 nonce 即被拒绝。
    """
    nonce = str(uuid.uuid4())
    try:
        cache.set(f"{_NONCE_PREFIX}{nonce}", "1", ttl=_NONCE_TTL)
    except Exception as e:
        logger.warning(f"issue login nonce failed: {e}")
    return nonce


def decrypt_login_password(
    encrypted_password: str,
    nonce: str,
    cache: CacheProvider,
) -> str:
    """解密登录密码，返回明文密码。

    AUTH_ENCRYPTION_ENABLED=false 时直通返回原值（联调模式）；
    开启时依次校验：nonce 一次性 → RSA 解密 → 密文结构（nonce 一致）
    → 时间戳窗口。任何一步失败均抛 AuthenticationException。
    """
    if not settings.auth.encryption_enabled:
        return encrypted_password

    # 1. nonce 一次性消费（原子 GETDEL；键不存在说明未签发/已使用/已过期）
    key = f"{_NONCE_PREFIX}{nonce}"
    consumed = cache.getdel(key)
    if consumed is None:
        logger.warning("login nonce missing or already consumed")
        raise AuthenticationException(message=_INVALID_CREDENTIALS)

    # 2. RSA 解密（算法原语见 utils/security.py）
    try:
        plain = rsa_decrypt(encrypted_password)
    except ValueError:
        raise AuthenticationException(message=_INVALID_CREDENTIALS) from None

    # 3. 密文结构：nonce|timestamp|password（nonce 必须与提交值一致，防拼接替换）
    parts = plain.split("|", 2)
    if len(parts) != 3 or parts[0] != nonce:
        logger.warning("login ciphertext structure invalid")
        raise AuthenticationException(message=_INVALID_CREDENTIALS)

    # 4. 时间戳窗口校验
    try:
        timestamp = int(parts[1])
    except ValueError:
        raise AuthenticationException(message=_INVALID_CREDENTIALS) from None
    if abs(time.time() - timestamp) > _TS_TOLERANCE_SECONDS:
        logger.warning("login ciphertext timestamp out of range")
        raise AuthenticationException(message=_INVALID_CREDENTIALS)

    password = parts[2]
    if not password:
        raise AuthenticationException(message=_INVALID_CREDENTIALS)
    return password


__all__ = ["issue_login_nonce", "decrypt_login_password", "_NONCE_TTL"]
