"""管理系统业务路由包（面向管理员，JWT 鉴权）。

聚合管理后台各版本路由，统一挂载 /admin 前缀（/api 前缀由顶层 router 叠加），
对外完整路径为 /api/admin/v1/...。
未来新增 v2 时，在 src/api/admin/v2/__init__.py 聚合后于此处 include 即可。
"""

from fastapi import APIRouter

from src.api.admin.v1 import v1_router as admin_v1_router
from src.constants import ADMIN_PREFIX

admin_router = APIRouter(prefix=ADMIN_PREFIX)
admin_router.include_router(admin_v1_router)

__all__ = ["admin_router"]
