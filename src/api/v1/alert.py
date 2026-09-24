#!/usr/bin/env python3
"""
告警接口

供外部监控系统（Prometheus Alertmanager、Sentry 等）通过 Webhook 调用，
以及管理员手动发送系统告警。

Endpoints:
    POST   /alerts:          发送系统告警（指定接收人）
    POST   /alerts/broadcast: 广播系统告警（全体活跃用户）
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.api.dependencies import (
    get_current_user,
    get_db_session,
    get_notification_dispatcher,
)
from src.api.response import success_response
from src.core.exceptions import ValidationException
from src.notification.dispatcher import NotificationDispatcher
from src.schemas.alert import AlertSendRequest
from src.schemas.auth import CurrentUserResponse
from src.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["系统告警"])


def _get_alert_service(
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    db_session: Session = Depends(get_db_session),
) -> AlertService:
    """获取告警服务实例。"""
    return AlertService(dispatcher=dispatcher, session=db_session)


@router.post(
    "",
    summary="发送系统告警",
    description="发送系统告警到指定接收人（供外部监控 Webhook 调用）",
)
async def send_alert(
    body: AlertSendRequest,
    request: Request,
    service: AlertService = Depends(_get_alert_service),
):
    """发送系统告警接口。

    外部监控系统（Prometheus Alertmanager、Sentry 等）可通过 Webhook
    调用此接口发送告警通知。

    此端点需要 API Key 认证（通过 metadata 中的 source 字段标识来源），
    不依赖用户登录态。
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
)
async def broadcast_alert(
    body: AlertSendRequest,
    request: Request,
    service: AlertService = Depends(_get_alert_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
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
