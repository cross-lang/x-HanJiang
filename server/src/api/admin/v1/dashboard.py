#!/usr/bin/env python3
"""仪表盘统计接口（仪表盘 = 多个面板 Panel 的集合）。

仪表盘的权限码为 dashboard:view；首页（登录后落点）相关接口在 home.py，权限码为 home:view。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_dashboard_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.services.admin.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["管理系统：仪表盘"])


@router.get(
    "/stats",
    summary="仪表盘统计数据",
    dependencies=[Depends(require_user_permission(PermissionCode.DASHBOARD_VIEW.mark))],
)
@permission(PermissionCode.DASHBOARD_VIEW)
def get_stats(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> JSONResponse:
    """获取仪表盘关键指标和趋势数据。"""
    data = service.get_stats()
    return success_response(data, request)
