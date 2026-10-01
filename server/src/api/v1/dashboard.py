#!/usr/bin/env python3
"""仪表盘统计接口。"""

from fastapi import APIRouter, Depends, Request

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    CurrentUser,
    get_current_user,
    get_dashboard_service,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


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
):
    """获取仪表盘关键指标和趋势数据。"""
    data = service.get_stats()
    return success_response(data, request)


@router.get(
    "/my-activity",
    summary="我的最近活动",
    dependencies=[Depends(require_user_permission(PermissionCode.DASHBOARD_VIEW.mark))],
)
@permission(PermissionCode.DASHBOARD_VIEW)
def get_my_activity(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    """获取当前用户的最近登录日志和操作日志（首页用）。"""
    data = service.get_my_activity(current_user.id)
    return success_response(data, request)
