#!/usr/bin/env python3
"""
中央路由注册模块

本模块负责将所有 API 路由模块统一注册到主路由器上，
采用统一前缀 /api/v1，确保 API 版本化管理。

"""

from fastapi import APIRouter

from src.api.v1 import audit, auth, files, health, login_log, role, security, user
from src.constants import API_PREFIX

api_router = APIRouter(prefix=API_PREFIX)

# 注册健康检查路由
api_router.include_router(health.router)

# 注册用户管理路由
api_router.include_router(user.router)

# 注册身份认证路由
api_router.include_router(auth.router)

# 注册角色管理路由
api_router.include_router(role.router)

# 注册登录日志路由
api_router.include_router(login_log.router)

# 注册审计日志路由
api_router.include_router(audit.router)

# 注册文件上传路由
api_router.include_router(files.router)

# 注册安全与 MFA 路由
api_router.include_router(security.router)
