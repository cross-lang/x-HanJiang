#!/usr/bin/env python3
"""
系统级通知渠道配置 & 运维监控接口
"""

from fastapi import APIRouter, Depends, Request

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    get_system_notification_service,
    require_user_permission,
)
from src.api.response import success_response
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
