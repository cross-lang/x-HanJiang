#!/usr/bin/env python3
"""全局搜索接口 — 跨实体关键字搜索（用户/角色/权限/开放平台应用/文件/通知/公告）。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_permission_service,
    get_search_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.services.admin.permission_service import PermissionService
from src.services.admin.search_service import SearchService

router = APIRouter(prefix="/search", tags=["管理系统：全局搜索"])

# 分类 → 查看权限编码
_CATEGORY_PERMS: dict[str, str] = {
    "users": PermissionCode.USER_VIEW.mark,
    "roles": PermissionCode.ROLE_VIEW.mark,
    "permissions": PermissionCode.ROLE_VIEW.mark,
    "apps": PermissionCode.OPENAPI_APP_VIEW.mark,
    "files": PermissionCode.FILE_VIEW.mark,
    "notices": PermissionCode.NOTIFICATION_VIEW.mark,
    "announcements": PermissionCode.ANNOUNCEMENT_VIEW.mark,
}


@router.get(
    "",
    summary="全局搜索",
    description="按关键字搜索用户/角色/权限/开放平台应用/文件/通知/公告，按分类返回前 N 条",
    dependencies=[Depends(require_user_permission(PermissionCode.SEARCH.mark))],
)
@permission(PermissionCode.SEARCH)
def search(
    request: Request,
    keyword: str,
    limit: int = 5,
    current_user: CurrentUser = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service),
    service: SearchService = Depends(get_search_service),
) -> JSONResponse:
    kw = (keyword or "").strip()
    if not kw:
        return success_response({}, request)
    limit = max(1, min(limit, 20))
    if "*" in (current_user.permissions or []):
        categories = list(_CATEGORY_PERMS.keys())
    else:
        categories = [
            cat for cat, perm in _CATEGORY_PERMS.items() if permission_service.has_permission(current_user.id, perm)
        ]
    result = service.search(keyword=kw, limit=limit, categories=categories)
    return success_response(result, request)
