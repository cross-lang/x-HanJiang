"""通知管理 API。

提供系统通知的发布（幂等、定向受众、多渠道强推）、撤回、重新发布、
列表、详情与投递明细查询。
系统级通知渠道的配置管理见 system_notification_config.py。
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_system_notification_service,
    get_user_operator_context,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.notification import (
    NotificationDeliveryListResponse,
    OperationResponse,
    PublishNotificationRequest,
    PublishResultResponse,
    SystemNotificationResponse,
)
from src.schemas.common import PaginatedResponse
from src.services.admin.system_notification_service import SystemNotificationService

router = APIRouter(prefix="/notifications", tags=["管理系统：系统通知管理"])


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
    operator = get_user_operator_context(current_user, request)
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
        operator=get_user_operator_context(current_user, request),
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
        operator=get_user_operator_context(current_user, request),
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
    summary="通知投递明细",
    description="分页查询该系统通知的外发投递明细（可按渠道/状态过滤），并返回各状态统计",
    response_model=NotificationDeliveryListResponse,
    dependencies=[Depends(require_user_permission(PermissionCode.NOTIFICATION_VIEW.mark))],
)
@permission(PermissionCode.NOTIFICATION_VIEW)
def list_notice_deliveries(
    notice_id: int,
    request: Request,
    channel: str | None = Query(None, description="按渠道过滤（email/sms/dingtalk/feishu）"),
    status: str | None = Query(None, description="按投递状态过滤（pending/success/failed/retrying）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: SystemNotificationService = Depends(get_system_notification_service),
) -> JSONResponse:
    """通知投递明细接口。

    按系统通知 ID 查询其外发投递记录（email/sms/dingtalk/feishu）；
    站内信投递不写入本表，由独立的 station_messages 表承载。

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

