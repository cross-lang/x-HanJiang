"""开放平台门户 v1 路由包。
聚合开放平台门户 v1 版本下的接口，统一挂载 /v1 前缀。
对外完整路径为 /api/open-portal/v1/...

开发者门户接口（会话 JWT + Redis 登录态，供 web/open 前端调用）：
auth（账号）/ developer（资料与认证）/ app（应用管理 + scope 目录）/ messages（站内信）。
"""

from fastapi import APIRouter

from src.api.open_portal.v1 import app, auth, developer, messages
from src.constants import API_VERSION_V1_PREFIX

v1_router = APIRouter(prefix=API_VERSION_V1_PREFIX)

v1_router.include_router(auth.router)

v1_router.include_router(developer.router)

v1_router.include_router(app.router)

v1_router.include_router(app.scopes_router)

v1_router.include_router(messages.router)

__all__ = ["v1_router"]
