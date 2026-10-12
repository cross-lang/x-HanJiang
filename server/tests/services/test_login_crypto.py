#!/usr/bin/env python3
"""登录密码加密编排单元测试（login_crypto：nonce 一次性 / 时间窗 / 开关直通）。"""

from __future__ import annotations

import base64
import time
from typing import Any

import pytest
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from src.core.config import settings
from src.core.exceptions import AuthenticationException
from src.services.login_crypto import decrypt_login_password, issue_login_nonce

# 密文编排固定使用 2048 位测试密钥（与生产 4096 的 OAEP 语义一致）
_TEST_KEY = RSA.generate(2048)


@pytest.fixture(autouse=True)
def _use_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """login_crypto 通过 utils.security.rsa_decrypt 解密，需将私钥单例替换为测试密钥。"""
    monkeypatch.setattr("src.utils.security._get_rsa_private_key", lambda: _TEST_KEY)


class FakeCache:
    """内存版缓存替身（对齐 login_crypto 使用到的 set / getdel 语义）。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self.store[key] = value

    def getdel(self, key: str) -> Any | None:
        return self.store.pop(key, None)


def _encrypt(plain: str) -> str:
    """用测试公钥 OAEP-SHA256 加密。"""
    public_key = RSA.import_key(_TEST_KEY.public_key().export_key(format="PEM").decode("ascii"))
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    return base64.b64encode(cipher.encrypt(plain.encode("utf-8"))).decode("ascii")


@pytest.fixture()
def cache() -> FakeCache:
    return FakeCache()


def _prepare(cache: FakeCache, nonce: str) -> None:
    """模拟公钥接口签发 nonce（预写缓存）。"""
    cache.set(f"auth:nonce:{nonce}", "1", ttl=300)


class TestIssueLoginNonce:
    def test_nonce_prewritten(self, cache: FakeCache) -> None:
        nonce = issue_login_nonce(cache)
        assert cache.store[f"auth:nonce:{nonce}"] == "1"

    def test_nonce_unique(self, cache: FakeCache) -> None:
        assert issue_login_nonce(cache) != issue_login_nonce(cache)


class TestDecryptLoginPassword:
    def test_success(self, cache: FakeCache) -> None:
        nonce = "n-0001"
        _prepare(cache, nonce)
        ts = int(time.time())
        cipher = _encrypt(f"{nonce}|{ts}|S3cret@123")
        assert decrypt_login_password(cipher, nonce, cache) == "S3cret@123"
        # nonce 已被消费
        assert cache.store.get(f"auth:nonce:{nonce}") is None

    def test_nonce_reuse_rejected(self, cache: FakeCache) -> None:
        nonce = "n-0002"
        _prepare(cache, nonce)
        cipher = _encrypt(f"{nonce}|{int(time.time())}|S3cret@123")
        assert decrypt_login_password(cipher, nonce, cache) == "S3cret@123"
        # 重放同一 nonce（同一密文）→ 拒绝
        with pytest.raises(AuthenticationException):
            decrypt_login_password(cipher, nonce, cache)

    def test_nonce_missing_rejected(self, cache: FakeCache) -> None:
        cipher = _encrypt(f"n-0003|{int(time.time())}|S3cret@123")
        with pytest.raises(AuthenticationException):
            decrypt_login_password(cipher, "n-0003", cache)

    def test_timestamp_out_of_range(self, cache: FakeCache) -> None:
        nonce = "n-0004"
        _prepare(cache, nonce)
        stale_ts = int(time.time()) - 600  # 超窗 5 分钟
        cipher = _encrypt(f"{nonce}|{stale_ts}|S3cret@123")
        with pytest.raises(AuthenticationException):
            decrypt_login_password(cipher, nonce, cache)

    def test_ciphertext_nonce_mismatch(self, cache: FakeCache) -> None:
        nonce = "n-0005"
        _prepare(cache, nonce)
        cipher = _encrypt(f"n-0005-other|{int(time.time())}|S3cret@123")
        with pytest.raises(AuthenticationException):
            decrypt_login_password(cipher, nonce, cache)

    def test_invalid_ciphertext(self, cache: FakeCache) -> None:
        nonce = "n-0006"
        _prepare(cache, nonce)
        with pytest.raises(AuthenticationException):
            decrypt_login_password("junk-cipher", nonce, cache)

    def test_invalid_timestamp_part(self, cache: FakeCache) -> None:
        nonce = "n-0007"
        _prepare(cache, nonce)
        cipher = _encrypt(f"{nonce}|not-a-number|S3cret@123")
        with pytest.raises(AuthenticationException):
            decrypt_login_password(cipher, nonce, cache)

    def test_empty_password(self, cache: FakeCache) -> None:
        nonce = "n-0008"
        _prepare(cache, nonce)
        cipher = _encrypt(f"{nonce}|{int(time.time())}|")
        with pytest.raises(AuthenticationException):
            decrypt_login_password(cipher, nonce, cache)


class TestEncryptionDisabledPassthrough:
    def test_passthrough_when_disabled(self, cache: FakeCache, monkeypatch: pytest.MonkeyPatch) -> None:
        """AUTH_ENCRYPTION_ENABLED=false：本地 curl 联调直通（不做任何校验）。"""
        monkeypatch.setattr(settings.auth, "encryption_enabled", False)
        assert decrypt_login_password("plain-password", "any-nonce", cache) == "plain-password"
