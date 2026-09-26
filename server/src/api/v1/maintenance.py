#!/usr/bin/env python3
"""
系统维护接口

管理员触发系统维护通知，广播给全体活跃用户。

Endpoints:
    POST   /maintenance/notify: 发送系统维护通知
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.api.permission_decorator import permission
from src.api.dependencies import (
    get_current_user,
    require_user_permission,
    get_db_session,
    get_notification_dispatcher,
)
from src.api.response import success_response
from src.notification.dispatcher import NotificationDispatcher
from src.schemas.alert import MaintenanceNotifyRequest
from src.schemas.auth import CurrentUser
from src.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["系统维护"])


def _get_maintenance_service(
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    db_session: Session = Depends(get_db_session),
) -> MaintenanceService:
    """获取维护通知服务实例。"""
    return MaintenanceService(dispatcher=dispatcher, session=db_session)


@router.post(
    "/notify",
    summary="发送系统维护通知",
    description="向全体活跃用户发送系统维护通知（管理员操作）",
    dependencies=[Depends(require_user_permission("maintenance:notify"))],
)
@permission("maintenance:notify", "发送维护通知", "maintenance", "notify")
async def notify_maintenance(
    body: MaintenanceNotifyRequest,
    request: Request,
    service: MaintenanceService = Depends(_get_maintenance_service),
):
    """发送系统维护通知接口。

    管理员填写维护时间和预计时长后，系统自动向全体活跃用户
    发送维护通知（走用户配置的通知渠道）。
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
