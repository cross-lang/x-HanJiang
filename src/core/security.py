#!/usr/bin/env python3
"""
密码安全工具

基于 bcrypt 实现密码哈希与校验，避免引入未安装的 passlib 依赖。

Functions:
    hash_password: 对明文密码进行 bcrypt 哈希
    verify_password: 校验明文密码与哈希是否匹配
"""

import bcrypt

# bcrypt 密码最大长度限制（字节），超出会抛 ValueError
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希。

    Args:
        password: 明文密码

    Returns:
        str: bcrypt 哈希字符串（含 salt，可直接存储）
    """
    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与 bcrypt 哈希是否匹配。

    Args:
        password: 明文密码
        password_hash: bcrypt 哈希字符串

    Returns:
        bool: 匹配返回 True，否则 False（含异常时返回 False）
    """
    if not password_hash:
        return False
    try:
        password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
