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
    get_system_notification_service,
    require_user_permission,
)
from src.api.response import success_response
from src.schemas.auth import CurrentUser
from src.schemas.notification import (
    NotificationRecordResponse,
    NotificationSendRequest,
    NotificationStatsResponse,
    UpdateNotificationConfigRequest,
)
from src.services.notification_service import NotificationService
from src.services.system_notification_service import SystemNotificationService

router = APIRouter(prefix="/notifications", tags=["通知管理"])


@router.post(
    "/send",
    summary="手动发送通知",
    description="手动触发一次通知发送（仅限管理员或调试使用）",
    dependencies=[Depends(require_user_permission("notification:create"))],
)
@permission("notification:create", "创建通知", "notification", "create")
def send_notification(
    request: Request,
    body: NotificationSendRequest,
    current_user: CurrentUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> JSONResponse:
    """手动发送通知。

    请求体示例（使用用户配置自动发送）::

        {
            "event_type": "user.password_changed",
            "variables": {"username": "张三", "changed_at": "2026-09-24 10:00"}
        }

    请求体示例（手动指定接收人，调试用）::

        {
            "event_type": "user.password_changed",
            "recipients": {"email": "zhangsan@example.com", "dingtalk": "zhangsan"},
            "variables": {"username": "张三", "changed_at": "2026-09-23 10:00"},
            "channels": ["email", "dingtalk"],
            "metadata": {"source": "admin_panel"}
        }

    各字段说明：
        - event_type: 事件类型，决定使用哪套模板。
        - variables: 模板变量，会注入到对应模板的 `{变量名}` 占位符中。
        - recipients: （可选）手动指定渠道→接收人映射，用于调试。
            省略则自动从当前用户的通知渠道配置中获取（已启用的渠道）。
        - channels: （可选，仅手动模式生效）指定实际发送的渠道，覆盖事件默认路由表。
        - metadata: （可选）扩展元数据，会写入通知记录，可用于追溯来源。

    Args:
        request: 当前请求对象。
        body: 通知发送请求体。
        current_user: 当前登录用户（自动发送模式下作为默认接收人）。
        notification_service: 通知业务服务。

    Returns:
        JSONResponse: 统一响应结构，data 为发送成功的通知记录列表。
    """
    if body.recipients:
        # 手动指定接收人（调试模式）
        records = notification_service.send_manual(
            event_type=body.event_type.value,
            recipients=body.recipients,
            variables=body.variables,
            channels=body.channels,
            metadata=body.metadata,
        )
    else:
        # 根据当前用户配置自动发送
        records = notification_service.send_for_user(
            user_id=current_user.id,
            event_type=body.event_type.value,
            variables=body.variables,
            metadata=body.metadata,
        )
    result = [NotificationRecordResponse.model_validate(r).model_dump() for r in records]
    return success_response(result, request)


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
    service: SystemNotificationService = Depends(get_system_notification_service),
):
    """获取所有系统通知渠道配置。

    Args:
        request: FastAPI 请求对象。
        service: 系统通知服务实例（依赖注入）。

    Returns:
        统一响应，包含全部通知渠道的配置项列表。
    """
    return success_response({"items": service.list_configs()}, request)


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
    service: SystemNotificationService = Depends(get_system_notification_service),
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
    service: SystemNotificationService = Depends(get_system_notification_service),
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
