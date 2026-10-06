"""系统通知渠道配置管理 API（管理员）。

提供系统级通知渠道的配置查询与更新、渠道连通性测试。
与系统通知的发布/撤回（notification.py）分离：本文件只面向"渠道配置"这一管理面。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_system_notification_config_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.enums import NotificationErrorCode
from src.constants.permissions import PermissionCode
from src.core.logger import logger
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.notification import (
    ChannelTestResponse,
    OperationResponse,
    SystemNotificationConfigResponse,
    UpdateNotificationConfigRequest,
)
from src.services.admin.system_notification_config_service import SystemNotificationConfigService

router = APIRouter(prefix="/notification-configs", tags=["管理系统：系统通知配置管理"])


@router.get(
    "",
    summary="获取所有系统通知渠道配置",
    response_model=SystemNotificationConfigResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_CONFIG.mark))],
)
@permission(PermissionCode.NOTIFICATION_CONFIG)
def list_configs(
    request: Request,
    service: SystemNotificationConfigService = Depends(get_system_notification_config_service),
) -> JSONResponse:
    """获取所有系统通知渠道配置。

    Args:
        request: FastAPI 请求对象。
        service: 系统通知服务实例（依赖注入）。

    Returns:
        统一响应，包含全部通知渠道的配置项列表。
    """
    items = [
        SystemNotificationConfigResponse.model_validate(cfg).model_dump()
        for cfg in service.list_configs()
    ]
    return success_response({"items": items}, request)


@router.put(
    "/{channel}",
    summary="更新某渠道配置",
    response_model=OperationResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_CONFIG.mark))],
)
@permission(PermissionCode.NOTIFICATION_CONFIG)
def update_config(
    channel: str,
    request: Request,
    body: UpdateNotificationConfigRequest,
    service: SystemNotificationConfigService = Depends(get_system_notification_config_service),
) -> JSONResponse:
    """更新指定通知渠道的配置。

    Args:
        channel: 通知渠道标识（如 email、dingtalk、feishu、station）。
        request: FastAPI 请求对象。
        body: 更新配置请求体（config 与 enabled）。
        service: 系统通知服务实例（依赖注入）。

    Returns:
        统一响应，标识更新是否成功。

    Raises:
        渠道不存在或配置非法时由服务层抛出业务异常。
    """
    service.update_config(
        channel=channel,
        config=body.config,
        enabled=body.enabled,
    )
    # 配置变更后立即重建 provider，无需重启
    from src.infras.notification import reload_providers_from_db

    reload_providers_from_db()
    return success_response(OperationResponse(message="配置已更新").model_dump(), request)


@router.post(
    "/{channel}/test",
    summary="发送测试消息",
    response_model=ChannelTestResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_CONFIG.mark))],
)
@permission(PermissionCode.NOTIFICATION_CONFIG)
def test_channel(
    channel: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """向指定渠道发送一条测试消息，验证配置是否可用。

    发送失败时不向前端透出底层异常详情，仅返回统一文案与错误码，详情落服务端日志。

    Args:
        channel: 渠道标识。
        request: FastAPI 请求对象。
        current_user: 当前登录用户（测试消息接收人）。

    Returns:
        统一响应，包含发送结果（success 与失败统一提示）。
    """
    from src.infras.notification import NotificationMessage, get_registry

    provider = get_registry().get(channel)
    if provider is None:
        return success_response(
            ChannelTestResponse(
                success=False,
                error="渠道未注册或未启用，请先完成渠道配置",
            ).model_dump(),
            request,
        )
    recipient = ""
    if channel == "email":
        recipient = current_user.email or ""
    elif channel in ("dingtalk", "feishu"):
        recipient = ""  # webhook 群广播不需要接收人
    elif channel == "station":
        recipient = str(current_user.id)
    try:
        ok = provider.send(
            NotificationMessage(
                recipient=recipient,
                subject="渠道测试",
                content=f"这是一条来自汉江管理系统的渠道测试消息（{channel}）。",
            )
        )
        return success_response(ChannelTestResponse(success=ok).model_dump(), request)
    except Exception as exc:  # noqa: BLE001 - 测试失败统一收敛，不暴露底层细节
        logger.warning("Channel test failed channel=%s: %s", channel, exc)
        return success_response(
            ChannelTestResponse(
                success=False,
                error=NotificationErrorCode.CHANNEL_TEST_FAILED.desc,
            ).model_dump(),
            request,
        )
