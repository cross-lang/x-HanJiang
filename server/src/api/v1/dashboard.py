#!/usr/bin/env python3
"""仪表盘统计接口。"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import CurrentUser, get_current_user
from src.api.response import success_response
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats", summary="仪表盘统计数据")
async def get_stats(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取仪表盘关键指标和趋势数据。"""
    service = DashboardService()
    data = service.get_stats()
    return success_response(data, request)
