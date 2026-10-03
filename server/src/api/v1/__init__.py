"""API v1 兼容层。
管理系统业务路由已收拢至 src/api/admin/v1/（HTTP 双路径 /api/v1/... 与 /api/admin/v1/... 兼容，功能一致）。
本文件仅保留向后兼容导入，不承载任何路由定义。
"""

from src.api.admin.v1 import v1_router  # noqa: F401

__all__ = ["v1_router"]
