#!/usr/bin/env python3
"""通用全局常量。

集中定义应用信息、环境标识、请求上下文键、响应消息、
用户字段约束等全局常量。禁止在业务代码中硬编码这些值。
"""

# -- 应用信息 -----------------------------------------------------------
APP_ID: str = "x-HanJiang"
APP_NAME: str = "汉江（HanJiang）"
APP_DESCRIPTION: str = "一个基于 FastAPI 框架深度封装的生产级 Python Web 应用框架"
APP_VERSION: str = "0.1.0"

# -- API ----------------------------------------------------------------
# 基础前缀；具体版本号（/v1）由各路由组在自己的 router 上声明，
# 例如：用户态 /api/v1，开放平台 /api/open/v1。
API_PREFIX: str = "/api"

# -- 环境标识 -----------------------------------------------------------
ENV_DEVELOPMENT: str = "development"
ENV_TESTING: str = "testing"
ENV_PRODUCTION: str = "production"

# -- 配置文件 -----------------------------------------------------------
DEFAULT_CONFIG_DIR: str = "."
DEFAULT_CONFIG_FILE: str = "config.yaml"

# -- 请求上下文 ---------------------------------------------------------
REQUEST_ID_HEADER: str = "X-Request-ID"        # 请求头中的 Request ID 字段名
CONTEXT_REQUEST_ID: str = "request_id"          # request.state 中的键
CONTEXT_REAL_IP: str = "real_ip"                # request.state 中的键

# -- 开放平台鉴权请求头（面向外部服务）--------
# plain 模式：X-App-Id + X-App-Key
# hmac 模式：X-App-Id + X-App-Date + X-App-Authorization
OPENAPI_HEADER_APP_ID: str = "X-App-Id"
OPENAPI_HEADER_APP_KEY: str = "X-App-Key"
OPENAPI_HEADER_DATE: str = "X-App-Date"
OPENAPI_HEADER_AUTHORIZATION: str = "X-App-Authorization"
OPENAPI_ALGORITHM: str = "HanJiang-1"
OPENAPI_SIGNATURE_WINDOW_SECONDS: int = 300

# -- 用户字段约束 -------------------------------------------------------
USERNAME_MIN_LENGTH: int = 3
USERNAME_MAX_LENGTH: int = 50

# -- 响应消息 -----------------------------------------------------------
MSG_SUCCESS: str = "success"
MSG_INTERNAL_ERROR: str = "Internal server error"
MSG_NOT_FOUND: str = "Resource not found"
MSG_VALIDATION_ERROR: str = "Validation error"
MSG_AUTHENTICATION_FAILED: str = "Authentication failed"
MSG_AUTHORIZATION_DENIED: str = "Permission denied"


