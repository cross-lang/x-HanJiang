"""开放平台 v1 路由包。
聚合开放平台 v1 版本下的接口，统一挂载 /v1 前缀。
对外完整路径为 /api/open/v1/...

两层接口：
- 网关接口（X-App-Id/X-App-Key）：health（健康）/ app（应用身份）/ user（用户能力）
- 开发者门户接口（JWT）：auth（账号）/ developer（资料与认证）/ apps（应用管理）/ scopes（scope 目录）
"""

from fastapi import APIRouter

from src.api.open.v1 import app, apps, auth, developer, health, scopes, user
from src.constants import API_VERSION_V1_PREFIX

v1_router = APIRouter(prefix=API_VERSION_V1_PREFIX)

v1_router.include_router(health.router)

v1_router.include_router(app.router)

v1_router.include_router(user.router)

v1_router.include_router(auth.router)

v1_router.include_router(developer.router)

v1_router.include_router(apps.router)

v1_router.include_router(scopes.router)

__all__ = ["v1_router"]
