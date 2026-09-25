"""开放平台 v1 路由包。

聚合开放平台 v1 版本下的接口，统一挂载 /v1 前缀。
对外完整路径为 /api/open/v1/...
"""

from fastapi import APIRouter

from src.api.open.v1 import health, ping

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(health.router)
v1_router.include_router(ping.router)

__all__ = ["v1_router"]
