#!/usr/bin/env python3
"""
中央路由注册模块
本模块只负责顶层路由分组，不关心具体版本号：
- /api/v1/...           → 管理系统业务接口（JWT 鉴权），版本聚合在 src/api/admin/v1/__init__.py
- /api/admin/v1/...     → 管理系统业务接口（同一组 handler 的双路径挂载，与 /api/v1/... 功能完全一致）
- /api/open/v1/...      → 开放平台接口（AppId/AppKey 鉴权），版本聚合在 src/api/open/v1/__init__.py
未来加 v2 时，只需新建 src/api/admin/v2/ 或 src/api/open/v2/，在对应 __init__.py
里建一个带 prefix="/v2" 的聚合 router，再在本文件 include 即可。
"""

from fastapi import APIRouter

from src.api.admin.v1 import v1_router as admin_v1_router
from src.api.open.v1 import v1_router as open_v1_router
from src.constants import API_PREFIX, OPEN_API_PREFIX

# 1. 管理系统业务路由（面向用户，JWT 鉴权）
# 双路径挂载：同一组 handler 同时响应 /api/v1/...（历史兼容）与 /api/admin/v1/...（收纳目录），功能完全一致
api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(admin_v1_router)
api_router.include_router(admin_v1_router, prefix="/admin")

# 2. 开放平台路由（面向外部服务，AppId/AppKey 鉴权）
open_router = APIRouter(prefix=OPEN_API_PREFIX)
open_router.include_router(open_v1_router)
