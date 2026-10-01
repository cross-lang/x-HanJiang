#!/usr/bin/env python3
"""
告警接口
发送系统告警到指定接收人，以及向全体活跃用户广播系统告警。
所有端点均需登录态与对应权限（alert:send / alert:broadcast）。

Endpoints:
    POST   /alerts:          发送系统告警（指定接收人）
    POST   /alerts/broadcast: 广播系统告警（全体活跃用户）
"""

from fastapi import APIRouter, Depends, Request

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    get_alert_service,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.alert import AlertSendRequest
from src.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["系统告警"])


@router.post(
    "",
    summary="发送系统告警",
    description="发送系统告警到指定接收人（需登录态与 alert:send 权限）",
    dependencies=[Depends(require_user_permission(PermissionCode.ALERT_SEND.mark))],
)
@permission(PermissionCode.ALERT_SEND)
def send_alert(
    body: AlertSendRequest,
    request: Request,
    service: AlertService = Depends(get_alert_service),
):
    """发送系统告警接口。

    向指定接收人发送告警通知，需 alert:send 权限。
    原外部监控 Webhook 直调场景如有需要，可改用 API Key / 开放平台鉴权通道接入。
    """
    records = service.send(
        subject=body.subject,
        message=body.message,
        recipients=body.recipients,
        metadata=body.metadata,
    )
    return success_response(
        {
            "sent": len(records),
            "success": sum(1 for r in records if r.status == "success"),
            "failed": sum(1 for r in records if r.status == "failed"),
        },
        request,
    )


@router.post(
    "/broadcast",
    summary="广播系统告警",
    description="广播系统告警给全体活跃用户（管理员操作）",
    dependencies=[Depends(require_user_permission(PermissionCode.ALERT_BROADCAST.mark))],
)
@permission(PermissionCode.ALERT_BROADCAST)
def broadcast_alert(
    body: AlertSendRequest,
    request: Request,
    service: AlertService = Depends(get_alert_service),
):
    """广播系统告警接口。
    仅管理员可调用，向全体活跃用户发送系统告警通知。
    """
    sent_count = service.broadcast(
        subject=body.subject,
        message=body.message,
        metadata=body.metadata,
    )
    return success_response(
        {"message": "告警广播完成", "sent_count": sent_count},
        request,
    )
