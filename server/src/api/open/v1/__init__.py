"""开放平台 v1 路由包。
聚合开放平台 v1 版本下的**网关接口**，统一挂载 /v1 前缀。
对外完整路径为 /api/open/v1/...

本包仅容纳开放接口（供外部应用调用汉江平台能力，鉴权 = X-App-Id/X-App-Key + HanJiang-1 签名）：
- health（健康检查）/ app（应用身份）/ user（用户能力）/ role（角色管理）/ file（文件管理）

开放平台门户自身的接口（开发者账号/应用管理，鉴权 = 门户会话 JWT）不在本包，
统一收拢于 src/api/open_portal/（对外路径 /api/open-portal/v1/...）。
"""

from fastapi import APIRouter

from src.api.open.v1 import app, file, health, role, user
from src.constants import API_VERSION_V1_PREFIX

v1_router = APIRouter(prefix=API_VERSION_V1_PREFIX)

v1_router.include_router(health.router)

v1_router.include_router(app.router)

v1_router.include_router(user.router)

v1_router.include_router(role.router)

v1_router.include_router(file.router)

__all__ = ["v1_router"]
