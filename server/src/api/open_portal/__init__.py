"""开放平台门户路由包（面向开发者网页端，鉴权 = 门户会话 JWT + Redis 登录态）。

聚合开放平台门户各版本路由，统一挂载 /open-portal 前缀（/api 前缀由顶层 router 叠加），
对外完整路径为 /api/open-portal/v1/...。

与开放接口（/api/open/v1/...，AppId/AppKey 签名鉴权）严格区分：
本包只承载开放平台网站页面自身的接口（开发者账号、个人中心、应用管理、scope 目录等），
调用方是 web/open_portal 前端，鉴权走开发者登录会话（参考管理系统登录会话管理模块实现）。
"""

from fastapi import APIRouter

from src.api.open_portal.v1 import v1_router as open_portal_v1_router
from src.constants import OPEN_PORTAL_PREFIX

open_portal_router = APIRouter(prefix=OPEN_PORTAL_PREFIX)
open_portal_router.include_router(open_portal_v1_router)

__all__ = ["open_portal_router"]
