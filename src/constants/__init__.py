#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常量定义模块

本目录统一存放项目中所有常量定义，禁止在业务代码中硬编码固定值。

设计原则：
    - 通用全局常量统一放置 common.py
    - 按业务模块拆分独立常量文件（user.py、order.py、goods.py）
    - 业务状态、标识统一使用Enum枚举实现，避免数字硬编码
"""

from src.constants.common import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    API_PREFIX,
    ENV_DEVELOPMENT,
    ENV_TESTING,
    ENV_PRODUCTION,
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_FILE,
    REQUEST_ID_HEADER,
    CONTEXT_REQUEST_ID,
    CONTEXT_REAL_IP,
    MSG_SUCCESS,
    MSG_INTERNAL_ERROR,
    MSG_NOT_FOUND,
    MSG_VALIDATION_ERROR,
    MSG_AUTHENTICATION_FAILED,
    MSG_AUTHORIZATION_DENIED,
)
from src.constants.user import (
    USERNAME_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    NAME_MAX_LENGTH,
    AGE_MIN,
    AGE_MAX,
    UserStatus,
)

__all__ = [
    "APP_ID",
    "APP_NAME",
    "APP_VERSION",
    "API_PREFIX",
    "ENV_DEVELOPMENT",
    "ENV_TESTING",
    "ENV_PRODUCTION",
    "DEFAULT_CONFIG_DIR",
    "DEFAULT_CONFIG_FILE",
    "REQUEST_ID_HEADER",
    "CONTEXT_REQUEST_ID",
    "CONTEXT_REAL_IP",
    "MSG_SUCCESS",
    "MSG_INTERNAL_ERROR",
    "MSG_NOT_FOUND",
    "MSG_VALIDATION_ERROR",
    "MSG_AUTHENTICATION_FAILED",
    "MSG_AUTHORIZATION_DENIED",
    "USERNAME_MIN_LENGTH",
    "USERNAME_MAX_LENGTH",
    "NAME_MIN_LENGTH",
    "NAME_MAX_LENGTH",
    "AGE_MIN",
    "AGE_MAX",
    "UserStatus",
]