#!/usr/bin/env python3
"""通用安全工具——加密原语与密码哈希。
本模块只放与业务无关的安全原语，供上层业务模块复用：
- SHA256 哈希
- HMAC-SHA256 签名计算
- Fernet 对称加解密（主密钥从 settings.auth.secret_key 派生）
- RSA-OAEP(SHA-256) 非对称加解密（登录密码加密传输；私钥来源配置驱动）
- bcrypt 密码哈希与校验
- 随机密钥生成
- 常量时间字符串比对（防时序侧信道）
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from pathlib import Path

import bcrypt
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from cryptography.fernet import Fernet

from src.core.config import settings
from src.core.logger import logger

# bcrypt 密码最大长度限制（字节），超出会抛 ValueError
_BCRYPT_MAX_BYTES = 72


# ============================================================
# 随机密钥
# ============================================================
def generate_secret_key() -> str:
    """生成随机安全密钥（用于 JWT 签名或密钥轮换）。

    Returns:
        str: 64 字符 URL-safe 随机字符串
    """
    return secrets.token_urlsafe(48)


# ============================================================
# bcrypt 密码哈希
# ============================================================


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希（含 salt，可直接存储）。"""
    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与 bcrypt 哈希是否匹配。异常时返回 False。"""
    if not password_hash:
        return False
    try:
        password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ============================================================
# SHA256
# ============================================================


def sha256_hex(text: str) -> str:
    """返回 text 的 SHA256 hex 摘要。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ============================================================
# 常量时间比对
# ============================================================


def constant_time_equals(a: str, b: str) -> bool:
    """常量时间字符串比对，防时序侧信道攻击。"""
    return hmac.compare_digest(a or "", b or "")


# ============================================================
# HMAC-SHA256
# ============================================================


def hmac_sha256_hex(key: str, message: str) -> str:
    """返回 HMAC-SHA256(key, message) 的 hex 摘要。"""
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ============================================================
# Fernet 对称加解密
# ============================================================

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """惰性构造 Fernet 实例。
    主密钥从 settings.auth.secret_key 派生（HKDF 语义：加固定 domain 前缀后 SHA256），
    不新增环境变量。注意：轮换 AUTH_SECRET_KEY 会导致已加密的密文无法解密，
    属于预期行为——轮换主密钥是大事，需要单独的重加密脚本。
    """
    global _fernet
    if _fernet is None:
        material = hashlib.sha256(f"hanjiang-master-key::{settings.auth.secret_key}".encode()).digest()
        _fernet = Fernet(base64.urlsafe_b64encode(material))
    return _fernet


def encrypt_text(plaintext: str) -> str:
    """加密任意字符串，返回 urlsafe 串落库。"""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str | None) -> str | None:
    """解密。密文为空或解密失败返回 None。"""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


# ============================================================
# RSA 非对称加解密（RSA-4096 / PKCS1_OAEP / SHA-256）
# ============================================================

_rsa_private_key: RSA.RsaKey | None = None


def _get_rsa_private_key() -> RSA.RsaKey:
    """惰性加载 RSA 私钥。

    来源优先级：AUTH_RSA_PRIVATE_KEY_PATH（PEM 文件，docker 挂载）
    > AUTH_RSA_PRIVATE_KEY（PEM 字符串，.env 中以 \\n 转义）
    > 未配置时生成临时 4096 密钥对（仅限开发兜底，重启后失效）。

    注意：轮换私钥会导致已加密的密文无法解密（预期行为，与 Fernet 主密钥同理）。
    """
    global _rsa_private_key
    if _rsa_private_key is None:
        if key_path := settings.auth.rsa_private_key_path:
            pem = Path(key_path).read_text(encoding="utf-8")
            logger.info(f"RSA 私钥从文件加载: {key_path}")
            _rsa_private_key = RSA.import_key(pem)
        elif pem := settings.auth.rsa_private_key:
            logger.info("RSA 私钥从环境变量加载")
            _rsa_private_key = RSA.import_key(pem)
        else:
            logger.warning("RSA_PRIVATE_KEY 未配置，使用临时密钥对（重启后失效，仅限开发环境）")
            _rsa_private_key = RSA.generate(4096)
    return _rsa_private_key


def rsa_public_key_pem() -> str:
    """导出公钥 PEM（下发给前端用于加密密码）。"""
    return _get_rsa_private_key().public_key().export_key(format="PEM").decode("ascii")


def rsa_decrypt(cipher_b64: str) -> str:
    """解密 base64 密文（OAEP-SHA256），返回明文。

    Raises:
        ValueError: 密文非法 / 解密失败
    """
    # 每次调用新建 cipher：pycryptodome 的 OAEP 对象含内部状态，并发下不可复用
    try:
        cipher = PKCS1_OAEP.new(_get_rsa_private_key(), hashAlgo=SHA256)
        plain = cipher.decrypt(base64.b64decode(cipher_b64))
        return plain.decode("utf-8")
    except Exception as e:
        logger.warning(f"RSA decrypt failed: {e}")
        raise ValueError("密文解密失败") from e


__all__ = [
    "generate_secret_key",
    "hash_password",
    "verify_password",
    "sha256_hex",
    "constant_time_equals",
    "hmac_sha256_hex",
    "encrypt_text",
    "decrypt_text",
    "rsa_public_key_pem",
    "rsa_decrypt",
]
