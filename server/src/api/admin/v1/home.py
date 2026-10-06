#!/usr/bin/env python3
"""首页接口（首页 = 登录成功后访问的页面）。

首页的权限码为 home:view；仪表盘（多个面板的集合）相关接口在 dashboard.py，权限码为 dashboard:view。
"""

from fastapi import APIRouter, Depends, Request

from src.api.admin.dependencies import (
    CurrentUser,
    get_current_user,
    get_dashboard_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.services.admin.dashboard_service import DashboardService

router = APIRouter(prefix="/home", tags=["管理系统：首页"])


@router.get(
    "/my-activity",
    summary="我的最近活动",
    dependencies=[Depends(require_user_permission(PermissionCode.HOME_VIEW.mark))],
)
@permission(PermissionCode.HOME_VIEW)
def get_my_activity(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    """获取当前用户的最近登录日志和操作日志（首页展示用）。

    Args:
        request: 当前请求对象
        current_user: 当前登录用户
        service: 仪表盘/首页共用活动查询服务

    Returns:
        统一响应结构，data 为最近活动数据
    """
    data = service.get_my_activity(current_user.id)
    return success_response(data, request)
