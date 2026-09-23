"""通知管理 API。

提供通知记录查询、统计和手动触发接口。
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.api.dependencies import (
    get_current_user,
    get_db_session,
    get_notification_dispatcher,
)
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.schemas.common import PaginatedResponse
from src.schemas.notification import (
    NotificationRecordResponse,
    NotificationSendRequest,
    NotificationStatsResponse,
)
from src.services.notification_dispatcher import NotificationDispatcher

router = APIRouter(prefix="/notifications", tags=["通知管理"])


@router.post(
    "/send",
    summary="手动发送通知",
    description="手动触发一次通知发送，用于调试和测试",
)
def send_notification(
    request: Request,
    body: NotificationSendRequest,
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """手动发送通知。

    请求体示例（使用用户配置自动发送）：
    ```json
    {
        "event_type": "user.registered",
        "variables": {
            "username": "张三"
        }
    }
    ```

    请求体示例（手动指定接收人，调试用）：
    ```json
    {
        "event_type": "user.password_changed",
        "recipients": {
            "email": "zhangsan@example.com",
            "dingtalk": "zhangsan"
        },
        "variables": {
            "username": "张三",
            "changed_at": "2026-09-23 10:00"
        },
        "channels": ["email", "dingtalk"],
        "metadata": {
            "source": "admin_panel"
        }
    }
    ```

    各字段说明：
    - event_type: 事件类型，决定使用哪套模板。可选值：
        `user.registered` / `user.password_reset` /
        `user.password_changed` / `user.profile_updated` /
        `user.status_changed` / `user.login_failed` /
        `role.assigned` / `permission.granted` / `permission.revoked` /
        `file.uploaded` / `file.shared` /
        `system.alert` / `system.maintenance`
    - variables: 模板变量，会注入到对应模板的 `{变量名}` 占位符中。
    - recipients: （可选）手动指定渠道→接收人映射，用于调试。
        省略则自动从当前用户的通知渠道配置中获取（已启用的渠道）。
    - channels: （可选，仅手动模式生效）指定实际发送的渠道，覆盖事件默认路由表。
    - metadata: （可选）扩展元数据，会写入通知记录，可用于追溯来源。
    """
    if body.recipients:
        # 手动指定接收人（调试模式）
        records = dispatcher.dispatch(
            event_type=body.event_type,
            recipients=body.recipients,
            variables=body.variables,
            channels=body.channels,
            metadata=body.metadata,
        )
    else:
        # 根据当前用户配置自动发送
        records = dispatcher.dispatch_for_user(
            user_id=current_user.id,
            event_type=body.event_type,
            variables=body.variables,
            metadata=body.metadata,
        )
    result = [NotificationRecordResponse.model_validate(r).model_dump() for r in records]
    return success_response(result, request)


@router.get(
    "",
    summary="通知列表",
    description="分页查询当前用户的通知发送记录",
)
def list_notifications(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    event_type: str | None = Query(None, description="按事件类型过滤"),
    channel: str | None = Query(None, description="按渠道过滤"),
    status: str | None = Query(None, description="按状态过滤"),
    db_session: Session = Depends(get_db_session),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """查询通知记录列表（分页）。"""
    from src.models.entities.notification_entity import NotificationRecordEntity

    query = db_session.query(NotificationRecordEntity)

    if event_type:
        query = query.filter(
            NotificationRecordEntity.event_type == event_type
        )
    if channel:
        query = query.filter(NotificationRecordEntity.channel == channel)
    if status:
        query = query.filter(NotificationRecordEntity.status == status)

    total = query.count()
    items = (
        query.order_by(NotificationRecordEntity.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = PaginatedResponse[NotificationRecordResponse](
        items=[NotificationRecordResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return success_response(result.model_dump(), request)


@router.get(
    "/stats",
    summary="通知统计",
    description="查询通知发送的成功/失败/待发送统计",
)
def get_notification_stats(
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """通知统计接口。"""
    from src.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(session=db_session)
    stats = NotificationStatsResponse(
        total=repo.count(),
        success=repo.count_by_status("success"),
        failed=repo.count_by_status("failed"),
        pending=repo.count_by_status("pending"),
    )
    return success_response(stats.model_dump(), request)


@router.get(
    "/{notification_id}",
    summary="通知详情",
    description="查询单条通知记录详情",
)
def get_notification(
    request: Request,
    notification_id: int,
    db_session: Session = Depends(get_db_session),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """查询单条通知记录。"""
    from src.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(session=db_session)
    record = repo.get_by_id(notification_id)
    if record is None:
        from src.core.exceptions import NotFoundException

        raise NotFoundException(message="通知记录不存在")

    result = NotificationRecordResponse.model_validate(record)
    return success_response(result.model_dump(), request)
