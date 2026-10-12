#!/usr/bin/env python3
"""通用安全工具单元测试（utils/security.py：RSA-OAEP 原语）。"""

from __future__ import annotations

import base64

import pytest
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from src.core.config import settings
from src.utils.security import _get_rsa_private_key, rsa_decrypt, rsa_public_key_pem


def _patch_test_key(monkeypatch: pytest.MonkeyPatch, bits: int = 2048) -> RSA.RsaKey:
    """将模块级 RSA 私钥单例替换为测试密钥（2048 位，往返语义与生产 4096 一致）。"""
    key = RSA.generate(bits)
    monkeypatch.setattr("src.utils.security._get_rsa_private_key", lambda: key)
    return key


def _encrypt_with_public(public_key_pem: str, plain: str) -> str:
    """模拟前端：用公钥 OAEP-SHA256 加密。"""
    public_key = RSA.import_key(public_key_pem)
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    return base64.b64encode(cipher.encrypt(plain.encode("utf-8"))).decode("ascii")


class TestRsaPrimitives:
    """RSA-OAEP(SHA-256) 原语（rsa_public_key_pem / rsa_decrypt）。"""

    def test_roundtrip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = _patch_test_key(monkeypatch)
        plain = "nonce-uuid|1780000000|S3cret@123"
        cipher_b64 = _encrypt_with_public(rsa_public_key_pem(), plain)
        assert rsa_decrypt(cipher_b64) == plain
        assert key.public_key().export_key(format="PEM").decode("ascii") == rsa_public_key_pem()

    def test_roundtrip_chinese_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """64 个中文字符 + nonce + 时间戳：用生产规格 4096 验证 OAEP 明文预算。

        2048 位 OAEP-SHA256 明文预算仅 190 字节（nonce+时间戳+64 中文超限），
        4096 位预算 446 字节才富余——这是生产固定使用 4096 的原因。
        """
        _patch_test_key(monkeypatch, bits=4096)
        plain = "nonce-36chars|1780000000|" + "汉" * 64
        cipher_b64 = _encrypt_with_public(rsa_public_key_pem(), plain)
        assert rsa_decrypt(cipher_b64) == plain

    def test_public_key_pem_stable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_test_key(monkeypatch)
        assert rsa_public_key_pem() == rsa_public_key_pem()

    def test_decrypt_invalid_base64_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_test_key(monkeypatch)
        with pytest.raises(ValueError):
            rsa_decrypt("not-base64!!!")

    def test_decrypt_wrong_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """用另一把公钥加密，本私钥解密应失败。"""
        _patch_test_key(monkeypatch)
        other = RSA.generate(2048)
        other_pub = other.public_key().export_key(format="PEM").decode("ascii")
        cipher_b64 = _encrypt_with_public(other_pub, "nonce|1780000000|pass")
        with pytest.raises(ValueError):
            rsa_decrypt(cipher_b64)

    def test_decrypt_empty_cipher_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_test_key(monkeypatch)
        with pytest.raises(ValueError):
            rsa_decrypt("")

    def test_load_from_env_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """私钥以 PEM 字符串注入（.env 场景）应可正常加载。"""
        key = RSA.generate(2048)
        pem = key.export_key(format="PEM").decode("ascii")
        monkeypatch.setattr(settings.auth, "rsa_private_key_path", "")
        monkeypatch.setattr(settings.auth, "rsa_private_key", pem)
        monkeypatch.setattr("src.utils.security._rsa_private_key", None)
        loaded = _get_rsa_private_key()
        expected_pem = key.public_key().export_key(format="PEM").decode("ascii")
        assert loaded.public_key().export_key(format="PEM").decode("ascii") == expected_pem
