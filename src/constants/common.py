#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用全局常量定义

本模块定义了应用程序级别的全局常量，包括应用信息、API 路径前缀、环境名称等。
所有模块中需要使用的全局常量必须在此文件中统一定义，禁止分散或硬编码。

Attributes:
    APP_ID: 应用唯一标识符
    APP_NAME: 应用显示名称
    APP_VERSION: 应用版本号
    API_PREFIX: API 路由统一前缀
    ENV_DEVELOPMENT: 开发环境标识
    ENV_TESTING: 测试环境标识
    ENV_PRODUCTION: 生产环境标识
    DEFAULT_CONFIG_DIR: 默认配置文件目录
"""

# ============================================================
# 应用信息
# ============================================================
APP_ID: str = "x-HanJiang"
APP_NAME: str = "寒江（HanJiang）"
APP_VERSION: str = "0.1.0"

# ============================================================
# API 配置
# ============================================================
API_PREFIX: str = "/api/v1"

# ============================================================
# 环境标识
# ============================================================
ENV_DEVELOPMENT: str = "development"
ENV_TESTING: str = "testing"
ENV_PRODUCTION: str = "production"

# ============================================================
# 配置文件
# ============================================================
DEFAULT_CONFIG_DIR: str = "config"
DEFAULT_CONFIG_FILE: str = "config.yaml"

# ============================================================
# 请求上下文键
# ============================================================
REQUEST_ID_HEADER: str = "X-Request-ID"
CONTEXT_REQUEST_ID: str = "request_id"
CONTEXT_REAL_IP: str = "real_ip"

# ============================================================
# 响应消息
# ============================================================
MSG_SUCCESS: str = "success"
MSG_INTERNAL_ERROR: str = "Internal server error"
MSG_NOT_FOUND: str = "Resource not found"
MSG_VALIDATION_ERROR: str = "Validation error"
MSG_AUTHENTICATION_FAILED: str = "Authentication failed"
MSG_AUTHORIZATION_DENIED: str = "Permission denied"