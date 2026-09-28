"""通知管理 API。

提供通知记录查询、统计、手动触发接口，以及系统级通知渠道的
配置查询与更新、渠道连通性测试、系统监控状态查询接口。
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.api_permission_decorator import permission
from src.api.dependencies import (
    get_current_user,
    get_notification_service,
    get_system_notification_config_service,
    get_system_notification_service,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.enums import SystemNotificationType
from src.schemas.auth import CurrentUser
from src.schemas.notification import (
    NotificationStatsResponse,
    PublishNotificationRequest,
    SystemNotificationResponse,
    UpdateNotificationConfigRequest,
)
from src.services.notification_service import NotificationService
from src.services.system_notification_config_service import SystemNotificationConfigService
from src.services.system_notification_service import SystemNotificationService

router = APIRouter(prefix="/notifications", tags=["通知管理"])


# ============================================================
# 系统通知（广播）管理：发布 / 撤回 / 列表 / 详情
# ============================================================


@router.post(
    "/publish",
    summary="发布系统通知",
    description="面向全体活跃用户发布系统通知（普通通知/系统维护），推送站内信产生未读红点",
    dependencies=[Depends(require_user_permission("notification:create"))],
)
@permission("notification:create", "创建通知", "notification", "create")
def publish_notice(
    request: Request,
    body: PublishNotificationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """发布系统通知接口。

    notice_type=maintenance 时按系统维护语义发布（维护时间/时长为必填），
    在站内信广播基础上额外按用户渠道配置推送多渠道通知。

    Args:
        request: 当前请求对象。
        body: 发布请求体（标题、正文、类型与维护参数）。
        current_user: 当前登录用户（记录操作人）。
        service: 系统通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为系统通知详情（维护类型附 sent_count）。
    """
    operator = {
        "operator_id": current_user.id,
        "operator_name": current_user.username,
    }
    if body.notice_type == SystemNotificationType.MAINTENANCE:
        notice_id, sent_count = service.publish_maintenance(
            title=body.title,
            maintenance_time=body.maintenance_time or "",
            duration=body.duration or "",
            reason=body.reason,
            operator=operator,
        )
        data = SystemNotificationResponse.model_validate(service.get_notice(notice_id)).model_dump()
        data["sent_count"] = sent_count
        return success_response(data, request)
    entity = service.publish(
        title=body.title,
        content=body.content,
        notice_type=body.notice_type,
        operator=operator,
    )
    data = SystemNotificationResponse.model_validate(entity).model_dump()
    return success_response(data, request)


@router.post(
    "/{notice_id}/withdraw",
    summary="撤回系统通知",
    description="撤回已发布的系统通知（幂等）",
    dependencies=[Depends(require_user_permission("notification:create"))],
)
@permission("notification:create", "创建通知", "notification", "create")
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
    return success_response({"message": "通知已撤回"}, request)


@router.get(
    "/published",
    summary="系统通知列表",
    description="分页查询已发布的系统通知（普通通知/系统维护）",
    dependencies=[Depends(require_user_permission("notification:view"))],
)
@permission("notification:view", "查看通知", "notification", "view")
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
    dependencies=[Depends(require_user_permission("notification:view"))],
)
@permission("notification:view", "查看通知", "notification", "view")
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
    "",
    summary="通知列表",
    description="分页查询当前用户的通知发送记录",
    dependencies=[Depends(require_user_permission("notification:view"))],
)
@permission("notification:view", "查看通知", "notification", "view")
def list_notifications(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    event_type: str | None = Query(None, description="按事件类型过滤"),
    channel: str | None = Query(None, description="按渠道过滤"),
    status: str | None = Query(None, description="按状态过滤"),
    notification_service: NotificationService = Depends(get_notification_service),
) -> JSONResponse:
    """查询通知记录列表（分页）。

    Args:
        request: 当前请求对象。
        page: 页码（从 1 开始）。
        page_size: 每页数量（1~100）。
        event_type: 事件类型过滤条件。
        channel: 渠道过滤条件。
        status: 状态过滤条件。
        notification_service: 通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为分页通知记录。
    """
    result = notification_service.list_records(
        page=page,
        page_size=page_size,
        event_type=event_type,
        channel=channel,
        status=status,
    )
    return success_response(result.model_dump(), request)


@router.get(
    "/stats",
    summary="通知统计",
    description="查询通知发送的成功/失败/待发送统计",
    dependencies=[Depends(require_user_permission("notification:view"))],
)
@permission("notification:view", "查看通知", "notification", "view")
def get_notification_stats(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service),
) -> JSONResponse:
    """通知统计接口。

    Args:
        request: 当前请求对象。
        notification_service: 通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为通知统计结果。
    """
    stats = NotificationStatsResponse(**notification_service.get_stats())
    return success_response(stats.model_dump(), request)


@router.get(
    "/{notification_id}",
    summary="通知详情",
    description="查询单条通知记录详情",
    dependencies=[Depends(require_user_permission("notification:view"))],
)
@permission("notification:view", "查看通知", "notification", "view")
def get_notification(
    request: Request,
    notification_id: int,
    notification_service: NotificationService = Depends(get_notification_service),
) -> JSONResponse:
    """查询单条通知记录。

    Args:
        request: 当前请求对象。
        notification_id: 通知记录 ID。
        notification_service: 通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为通知记录详情。
    """
    result = notification_service.get_record(notification_id)
    return success_response(result.model_dump(), request)


# ============================================================
# 系统通知渠道配置管理（管理员）
# ============================================================

admin_router = APIRouter(prefix="/admin/notification-configs", tags=["通知管理"])


@admin_router.get(
    "",
    summary="获取所有系统通知渠道配置",
    dependencies=[Depends(require_user_permission("notification:config"))],
)
@permission("notification:config", "通知配置管理", "notification", "config")
def list_configs(
    request: Request,
    service: SystemNotificationConfigService = Depends(get_system_notification_config_service),
):
    """获取所有系统通知渠道配置。

    Args:
        request: FastAPI 请求对象。
        service: 系统通知服务实例（依赖注入）。

    Returns:
        统一响应，包含全部通知渠道的配置项列表。
    """
    items = [
        {
            "id": cfg.id,
            "channel": cfg.channel,
            "config_json": cfg.config_json,
            "enabled": cfg.enabled,
        }
        for cfg in service.list_configs()
    ]
    return success_response({"items": items}, request)


@admin_router.put(
    "/{channel}",
    summary="更新某渠道配置",
    dependencies=[Depends(require_user_permission("notification:config"))],
)
@permission("notification:config", "通知配置管理", "notification", "config")
def update_config(
    channel: str,
    request: Request,
    body: UpdateNotificationConfigRequest,
    service: SystemNotificationConfigService = Depends(get_system_notification_config_service),
):
    """更新指定通知渠道的配置。

    Args:
        channel: 通知渠道标识（如 email、dingtalk、feishu、station）。
        request: FastAPI 请求对象。
        body: 更新配置请求体（config_json 与 enabled）。
        service: 系统通知服务实例（依赖注入）。

    Returns:
        统一响应，标识更新是否成功。

    Raises:
        渠道不存在或配置非法时由服务层抛出业务异常。
    """
    service.update_config(
        channel=channel,
        config_json=body.config_json,
        enabled=body.enabled,
    )
    # 配置变更后立即重建 provider，无需重启
    from src.infras.notification import reload_providers_from_db

    reload_providers_from_db()
    return success_response({"updated": True}, request)


@admin_router.get(
    "/monitor/system",
    summary="系统监控状态",
    dependencies=[Depends(require_user_permission("notification:config"))],
)
@permission("notification:config", "通知配置管理", "notification", "config")
def system_monitor(
    request: Request,
    service: SystemNotificationConfigService = Depends(get_system_notification_config_service),
):
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
    dependencies=[Depends(require_user_permission("notification:config"))],
)
@permission("notification:config", "通知配置管理", "notification", "config")
def test_channel(
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
        ok = provider.send(
            NotificationMessage(
                recipient=recipient,
                subject="渠道测试",
                content=f"这是一条来自汉江管理系统的渠道测试消息（{channel}）。",
            )
        )
        return success_response({"success": ok}, request)
    except Exception as exc:
        return success_response({"success": False, "error": str(exc)}, request)
