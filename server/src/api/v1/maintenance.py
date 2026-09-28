#!/usr/bin/env python3
"""
系统维护接口
管理员触发系统维护通知，广播给全体活跃用户。

Endpoints:
    POST   /maintenance/notify: 发送系统维护通知
"""

from fastapi import APIRouter, Depends, Request

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    get_current_user,
    get_maintenance_service,
    require_user_permission,
)
from src.api.response import success_response
from src.schemas.alert import MaintenanceNotifyRequest
from src.schemas.auth import CurrentUser
from src.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["系统维护"])


@router.post(
    "/notify",
    summary="发送系统维护通知",
    description="向全体活跃用户发送系统维护通知（管理员操作）",
    dependencies=[Depends(require_user_permission("maintenance:notify"))],
)
@permission("maintenance:notify", "发送维护通知", "maintenance", "notify")
def notify_maintenance(
    body: MaintenanceNotifyRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: MaintenanceService = Depends(get_maintenance_service),
):
    """发送系统维护通知接口。
    管理员填写维护时间和预计时长后，系统自动向全体活跃用户
    发送维护通知（走用户配置的通知渠道）。

    Args:
        body: 维护通知请求体
        request: 当前请求对象
        current_user: 当前登录用户（记录操作人）
        service: 维护通知业务服务

    Returns:
        统一响应结构，包含发送数量与维护时间信息
    """
    sent_count = service.notify_all(
        maintenance_time=body.maintenance_time,
        duration=body.duration,
        reason=body.reason,
        metadata={"operator": current_user.username},
    )
    return success_response(
        {
            "message": "维护通知发送完成",
            "sent_count": sent_count,
            "maintenance_time": body.maintenance_time,
            "duration": body.duration,
        },
        request,
    )
