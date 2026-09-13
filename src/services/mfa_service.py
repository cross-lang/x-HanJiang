#!/usr/bin/env python3
"""MFA / 二步验证基础能力。"""

import base64
import hashlib
import hmac
import time
from typing import Any


class MFAService:
    """基于 TOTP 的双因素认证支持。"""

    @staticmethod
    def generate_secret() -> str:
        return base64.b32encode(hashlib.sha256(b"hanjiang-mfa-secret").digest()[:10]).decode("ascii").rstrip("=")

    @staticmethod
    def generate_code(secret: str, timestamp: int | None = None) -> int:
        ts = timestamp if timestamp is not None else int(time.time() // 30)
        key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
        counter = ts.to_bytes(length=8, byteorder="big", signed=False)
        digest = hmac.new(key, counter, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        binary = ((digest[offset] & 0x7F) << 24) | ((digest[offset + 1] & 0xFF) << 16) | ((digest[offset + 2] & 0xFF) << 8) | (digest[offset + 3] & 0xFF)
        return binary % 1_000_000

    @staticmethod
    def verify_code(secret: str, code: str | int, window: int = 1) -> bool:
        expected = int(code)
        current_ts = int(time.time() // 30)
        for offset in range(-window, window + 1):
            if MFAService.generate_code(secret, current_ts + offset) == expected:
                return True
        return False

    @staticmethod
    def build_otpauth_url(account: str, secret: str, issuer: str = "HanJiang") -> str:
        return f"otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}&digits=6&period=30"
