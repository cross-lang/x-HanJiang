#!/usr/bin/env python3
"""
系统级通知渠道配置 & 运维监控接口
"""

from fastapi import APIRouter, Depends, Request

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    get_current_user,
    get_system_notification_service,
    require_user_permission,
)
from src.api.response import success_response
from src.schemas.auth import CurrentUser
from src.services.system_notification_service import SystemNotificationService

router = APIRouter(prefix="/admin/notification-configs", tags=["系统通知配置"])


@router.get(
    "",
    summary="获取所有系统通知渠道配置",
    dependencies=[Depends(require_user_permission("alert:broadcast"))],
)
async def list_configs(
    request: Request,
    service: SystemNotificationService = Depends(get_system_notification_service),
):
    return success_response({"items": service.list_configs()}, request)


@router.put(
    "/{channel}",
    summary="更新某渠道配置",
    dependencies=[Depends(require_user_permission("alert:broadcast"))],
)
async def update_config(
    channel: str,
    request: Request,
    body: dict,
    service: SystemNotificationService = Depends(get_system_notification_service),
):
    service.update_config(
        channel=channel,
        config_json=body.get("config_json", "{}"),
        enabled=body.get("enabled", True),
    )
    # 配置变更后立即重建 provider，无需重启
    from src.infras.notification import reload_providers_from_db
    reload_providers_from_db()
    return success_response({"updated": True}, request)


@router.get(
    "/monitor/system",
    summary="系统监控状态",
    dependencies=[Depends(require_user_permission("alert:broadcast"))],
)
async def system_monitor(
    request: Request,
    service: SystemNotificationService = Depends(get_system_notification_service),
):
    return success_response(service.get_system_monitor(), request)


@router.post(
    "/{channel}/test",
    summary="发送测试消息",
    dependencies=[Depends(require_user_permission("alert:broadcast"))],
)
async def test_channel(
    channel: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """向指定渠道发送一条测试消息，验证配置是否可用。"""
    from src.infras.notification import NotificationMessage, get_registry

    provider = get_registry().get(channel)
    if provider is None:
        return success_response({"success": False, "error": f"渠道 {channel} 未注册或未启用"}, request)

    recipient = ""
    if channel == "email":
        recipient = current_user.email or ""
    elif channel in ("dingtalk", "feishu"):
        recipient = ""  # webhook 群广播不需要接收人
    elif channel == "station":
        recipient = str(current_user.id)

    try:
        ok = provider.send(NotificationMessage(
            recipient=recipient,
            subject="渠道测试",
            content=f"这是一条来自汉江管理系统的渠道测试消息（{channel}）。",
        ))
        return success_response({"success": ok}, request)
    except Exception as exc:
        return success_response({"success": False, "error": str(exc)}, request)
