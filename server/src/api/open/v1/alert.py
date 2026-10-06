#!/usr/bin/env python3
"""开放 API 告警推送接口。

外部系统通过 AppId/AppKey 签名调用本接口发送系统告警，
告警将自动推送给超级管理员（邮箱/短信）以及系统通知配置中已启用的渠道。
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.api.open.dependencies import (
    CurrentApp,
    get_alert_service,
    get_current_app,
    require_app_scope,
)
from src.api.open.scope_decorator import app_scope
from src.api.response import success_response
from src.constants.scopes import OpenApiScopeCode
from src.schemas.common import ApiResponse
from src.services.admin.alert_service import AlertService

router = APIRouter(tags=["开放API：告警推送"])


class AlertSendRequest(BaseModel):
    """发送告警请求体。"""

    subject: str = Field(..., description="告警标题", max_length=200)
    message: str = Field(..., description="告警内容", max_length=2000)
    recipients: dict[str, str] = Field(
        default_factory=dict,
        description="额外接收人（渠道→地址，如 {\"email\": \"a@b.com\"}），超管渠道自动追加",
    )


@router.post(
    "/alert/send",
    summary="发送系统告警",
    response_model=ApiResponse,
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.ALERT_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.ALERT_WRITE)
def send_alert(
    body: AlertSendRequest,
    request: Request,
    app: CurrentApp = Depends(get_current_app),
    service: AlertService = Depends(get_alert_service),
):
    """发送系统告警通知（需 `alert:write` scope）。

    告警将自动推送到：
    1. 超级管理员的邮箱
    2. 超级管理员绑定的手机号（短信）
    3. 系统通知配置中已启用的钉钉/飞书 webhook

    调用方可通过 recipients 追加额外接收人。
    """
    deliveries = service.send(
        subject=body.subject,
        message=body.message,
        recipients=body.recipients,
        metadata={"source_app": app.name, "source_app_id": app.app_id},
    )
    return success_response(
        {"delivered": len(deliveries), "message": "告警已发送"},
        request,
    )
