"""API v1 路由包。"""

from src.api.v1.alert import router as alert_router
from src.api.v1.auth import router as auth_router
from src.api.v1.health import router as health_router
from src.api.v1.maintenance import router as maintenance_router
from src.api.v1.role import router as role_router
from src.api.v1.user import router as user_router

__all__ = [
    "alert_router",
    "auth_router",
    "health_router",
    "maintenance_router",
    "role_router",
    "user_router",
]
