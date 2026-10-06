"""通知管理 API。

提供系统通知的发布（幂等、定向受众、多渠道强推）、撤回、重新发布、
列表、详情与投递明细查询；以及系统级通知渠道的配置查询与更新、
渠道连通性测试、系统监控状态查询接口。
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_system_notification_config_service,
    get_system_notification_service,
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
    PublishNotificationRequest,
    PublishResultResponse,
    SystemNoticeDeliveryListResponse,
    SystemNotificationConfigResponse,
    SystemNotificationResponse,
    UpdateNotificationConfigRequest,
)
from src.schemas.common import PaginatedResponse
from src.services.admin.system_notification_config_service import SystemNotificationConfigService
from src.services.admin.system_notification_service import SystemNotificationService

router = APIRouter(prefix="/notifications", tags=["管理系统：通知管理"])


# ============================================================
# 系统通知（广播）管理：发布 / 撤回 / 重新发布 / 列表 / 详情 / 投递明细
# ============================================================


@router.post(
    "/publish",
    summary="发布系统通知",
    description="面向目标受众发布系统通知（普通通知/系统维护），推送站内信产生未读红点；"
    "支持幂等键（client_request_id）、定向受众（all/roles/users）与多渠道强推",
    response_model=PublishResultResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_CREATE.mark))],
)
@permission(PermissionCode.NOTIFICATION_CREATE)
def publish_notice(
    request: Request,
    body: PublishNotificationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """发布系统通知接口。

    通知类型（普通通知/系统维护）仅表达语义标签；
    携带维护参数（maintenance_time/duration_hours）时正文由系统按维护参数自动拼接；
    指定 target_type/target_roles/target_user_ids 时定向发布而非全员广播；
    指定 client_request_id 时同一请求键重复提交返回首次结果（幂等）。

    Args:
        request: 当前请求对象。
        body: 发布请求体（标题、正文、类型、维护参数、强推渠道、幂等键、受众）。
        current_user: 当前登录用户（记录操作人）。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为通知详情（含 sent_count 与 idempotent）。
    """
    operator = {
        "operator_id": current_user.id,
        "operator_name": current_user.username,
    }
    entity, sent_count, idempotent = service.publish(
        title=body.title,
        content=body.content,
        notice_type=body.notice_type,
        maintenance_time=body.maintenance_time,
        duration_hours=body.duration_hours,
        reason=body.reason,
        push_channels=[ch.value for ch in body.push_channels] if body.push_channels else None,
        client_request_id=body.client_request_id,
        target_type=body.target_type,
        target_roles=body.target_roles,
        target_user_ids=body.target_user_ids,
        operator=operator,
    )
    data = PublishResultResponse.model_validate(entity).model_dump()
    data["sent_count"] = sent_count
    data["idempotent"] = idempotent
    return success_response(data, request)


@router.post(
    "/{notice_id}/withdraw",
    summary="撤回系统通知",
    description="撤回已发布的系统通知（幂等，已撤回则直接返回）",
    response_model=OperationResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_WITHDRAW.mark))],
)
@permission(PermissionCode.NOTIFICATION_WITHDRAW)
def withdraw_notice(
    notice_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """撤回系统通知接口。

    Args:
        notice_id: 系统通知 ID。
        request: 当前请求对象。
        current_user: 当前登录用户（记录操作人）。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构。
    """
    service.withdraw(
        notice_id=notice_id,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response(OperationResponse(message="通知已撤回").model_dump(), request)


@router.post(
    "/{notice_id}/republish",
    summary="重新发布已撤回的通知",
    description="将已撤回的系统通知按首次发布的受众快照重新广播（站内信重新推送产生新红点）",
    response_model=PublishResultResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_CREATE.mark))],
)
@permission(PermissionCode.NOTIFICATION_CREATE)
def republish_notice(
    notice_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """重新发布系统通知接口（仅限已撤回状态）。

    Args:
        notice_id: 系统通知 ID。
        request: 当前请求对象。
        current_user: 当前登录用户（记录操作人）。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为通知详情（含 sent_count）。
    """
    entity, sent_count = service.republish(
        notice_id=notice_id,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    data = PublishResultResponse.model_validate(entity).model_dump()
    data["sent_count"] = sent_count
    return success_response(data, request)


@router.get(
    "/published",
    summary="系统通知列表",
    description="分页查询已发布的系统通知（普通通知/系统维护），支持类型/状态过滤与关键字搜索",
    response_model=PaginatedResponse[SystemNotificationResponse],
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_VIEW.mark))],
)
@permission(PermissionCode.NOTIFICATION_VIEW)
def list_published_notices(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    notice_type: str | None = Query(None, description="按通知类型过滤"),
    status: str | None = Query(None, description="按发布状态过滤"),
    keyword: str | None = Query(None, description="按标题/正文关键字搜索"),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """系统通知列表接口。

    Args:
        request: 当前请求对象。
        page: 页码。
        page_size: 每页数量。
        notice_type: 通知类型过滤（notice/maintenance）。
        status: 发布状态过滤（published/withdrawn）。
        keyword: 标题/正文关键字搜索。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为分页系统通知列表。
    """
    result = service.list_notices(
        page=page,
        page_size=page_size,
        notice_type=notice_type,
        status=status,
        keyword=keyword,
    )
    return success_response(result.model_dump(), request)


@router.get(
    "/published/{notice_id}",
    summary="系统通知详情",
    description="查询单条系统通知详情",
    response_model=SystemNotificationResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_VIEW.mark))],
)
@permission(PermissionCode.NOTIFICATION_VIEW)
def get_published_notice(
    notice_id: int,
    request: Request,
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """系统通知详情接口。

    Args:
        notice_id: 系统通知 ID。
        request: 当前请求对象。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为系统通知详情。
    """
    result = service.get_notice(notice_id)
    return success_response(result.model_dump(), request)


@router.get(
    "/{notice_id}/deliveries",
    summary="系统通知投递明细",
    description="分页查询系统通知的投递明细（可按渠道/状态过滤），并返回各状态统计",
    response_model=SystemNoticeDeliveryListResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_VIEW.mark))],
)
@permission(PermissionCode.NOTIFICATION_VIEW)
def list_notice_deliveries(
    notice_id: int,
    request: Request,
    channel: str | None = Query(None, description="按渠道过滤（station/email/dingtalk/feishu/sms）"),
    status: str | None = Query(None, description="按投递状态过滤（pending/success/failed）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """系统通知投递明细接口。

    Args:
        notice_id: 系统通知 ID。
        request: 当前请求对象。
        channel: 渠道过滤。
        status: 投递状态过滤。
        page: 页码。
        page_size: 每页数量。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为投递明细分页与状态统计。
    """
    result = service.get_deliveries(
        notice_id=notice_id,
        channel=channel,
        status=status,
        page=page,
        page_size=page_size,
    )
    return success_response(result.model_dump(), request)


# ============================================================
# 系统通知渠道配置管理（管理员）
# ============================================================

admin_router = APIRouter(prefix="/admin/notification-configs", tags=["管理系统：通知管理"])


@admin_router.get(
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


@admin_router.put(
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


@admin_router.get(
    "/monitor/system",
    summary="系统监控状态",
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_CONFIG.mark))],
)
@permission(PermissionCode.NOTIFICATION_CONFIG)
def system_monitor(
    request: Request,
    service: SystemNotificationConfigService = Depends(get_system_notification_config_service),
) -> JSONResponse:
    """获取系统通知监控状态。

    Args:
        request: FastAPI 请求对象。
        service: 系统通知服务实例（依赖注入）。

    Returns:
        统一响应，包含系统通知相关的监控指标与状态信息。
    """
    return success_response(service.get_system_monitor(), request)


@admin_router.post(
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
