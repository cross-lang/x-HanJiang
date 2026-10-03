#!/usr/bin/env python3
"""
中央路由注册模块
本模块只负责顶层路由分组，不关心具体版本号：
- /api/v1/...、/api/admin/v1/... → 管理系统业务接口（JWT 会话鉴权），版本聚合在 src/api/admin
- /api/open-portal/v1/...        → 开放平台门户接口（开发者会话 JWT + Redis），版本聚合在 src/api/open_portal
- /api/open/v1/...               → 开放接口（AppId/AppKey + HanJiang-1 签名），版本聚合在 src/api/open
"""

from fastapi import APIRouter

from src.api.admin import admin_router
from src.api.admin.v1 import v1_router as admin_v1_router
from src.api.open import open_router
from src.api.open_portal import open_portal_router
from src.constants import API_PREFIX

# 1. 管理系统业务路由（面向管理员，会话 JWT + Redis 登录态）
# 双路径挂载：同一组 handler 同时响应 /api/v1/...（历史兼容）与 /api/admin/v1/...（收纳目录），功能完全一致
global_admin_router = APIRouter(prefix=API_PREFIX)
global_admin_router.include_router(admin_v1_router)
global_admin_router.include_router(admin_router)

# 2. 开放平台门户路由（面向开发者门户网页端，会话 JWT + Redis 登录态）
global_open_portal_router = APIRouter(prefix=API_PREFIX)
global_open_portal_router.include_router(open_portal_router)

# 3. 开放接口路由（面向外部应用，AppId/AppKey 签名鉴权）
global_open_router = APIRouter(prefix=API_PREFIX)
global_open_router.include_router(open_router)
