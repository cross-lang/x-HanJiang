"""开放 API 路由包（面向外部服务，AppId/AppKey 鉴权）。

聚合开放 API 各版本路由，统一挂载 /open 前缀（/api 前缀由顶层 router 叠加），
对外完整路径为 /api/open/v1/...。
未来新增 v2 时，在 src/api/open/v2/__init__.py 聚合后于此处 include 即可。
"""

from fastapi import APIRouter

from src.api.open.v1 import v1_router as open_v1_router
from src.constants import OPEN_PREFIX

open_router = APIRouter(prefix=OPEN_PREFIX)
open_router.include_router(open_v1_router)

__all__ = ["open_router"]
