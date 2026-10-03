#!/usr/bin/env python3
"""
中央路由注册模块
本模块只负责顶层路由分组，不关心具体版本号：
- /api/v1/...           → 管理系统业务接口（JWT 鉴权，历史兼容路径），版本聚合在 src/api/admin/v1/__init__.py
- /api/admin/v1/...     → 管理系统业务接口（同一组 handler 的双路径挂载），版本聚合在 src/api/admin/__init__.py
- /api/open/v1/...      → 开放平台接口（AppId/AppKey 鉴权），版本聚合在 src/api/open/__init__.py
"""

from fastapi import APIRouter

from src.api.admin import admin_router
from src.api.admin.v1 import v1_router as admin_v1_router
from src.api.open import open_router as open_v1_router
from src.constants import API_PREFIX

# 1. 管理系统业务路由（面向管理员，JWT 鉴权）
# 双路径挂载：同一组 handler 同时响应 /api/v1/...（历史兼容）与 /api/admin/v1/...（收纳目录），功能完全一致
api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(admin_v1_router)
api_router.include_router(admin_router)

# 2. 开放平台路由（面向开放服务，AppId/AppKey 鉴权）
open_router = APIRouter(prefix=API_PREFIX)
open_router.include_router(open_v1_router)
