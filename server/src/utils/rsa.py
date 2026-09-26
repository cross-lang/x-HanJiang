#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSA 加密解密模块

提供基于 RSA 公钥/私钥的加密与解密能力，支持从密钥文件加载并对字符串进行 Base64 编码封装。
使用 OAEP 填充方案，比 PKCS1 更安全。
"""

import base64
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256


class RSATool:
    """ RSA加密解密工具，使用 OAEP 填充 """
    def __init__(self, public_key_path: str | Path | None = None, private_key_path: str | Path | None = None) -> None:
        self._public_key: RSA.RsaKey | None = None
        self._private_key: RSA.RsaKey | None = None

        if public_key_path:
            try:
                self._public_key = RSA.import_key(Path(public_key_path).read_bytes())
            except Exception:
                self._public_key = None

        if private_key_path:
            try:
                self._private_key = RSA.import_key(Path(private_key_path).read_bytes())
            except Exception:
                self._private_key = None

    def encrypt_data(self, data: str) -> str | None:
        if self._public_key is None:
            return None
        try:
            cipher = PKCS1_OAEP.new(self._public_key, hashAlgo=SHA256)
            encrypted = cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception:
            return None

    def decrypt_data(self, data: str) -> str | None:
        if self._private_key is None:
            return None
        try:
            cipher = PKCS1_OAEP.new(self._private_key, hashAlgo=SHA256)
            decrypted = cipher.decrypt(base64.b64decode(data.encode()))
            return decrypted.decode()
        except Exception:
            return None
