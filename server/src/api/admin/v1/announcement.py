"""公告管理 API。

提供公告的创建、修改、删除、发布、下架、列表与详情接口，
以及面向首页的生效公告查询接口（所有登录用户可见）。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from src.api.admin.permission_decorator import permission
from src.api.dependencies import (
    get_announcement_service,
    get_current_user,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.enums import AnnouncementStatus
from src.constants.permissions import PermissionCode
from src.models.entities.announcement_entity import AnnouncementEntity
from src.schemas.admin.announcement import (
    AnnouncementCreateRequest,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
)
from src.schemas.admin.auth import CurrentUser
from src.schemas.common import PaginatedResponse
from src.services.admin.announcement_service import AnnouncementService

router = APIRouter(prefix="/announcements", tags=["公告管理"])


def _to_response(entity: AnnouncementEntity) -> AnnouncementResponse:
    """公告实体转响应模型，并计算是否已过期。

    Args:
        entity: 公告实体

    Returns:
        AnnouncementResponse: 公告响应模型
    """
    resp = AnnouncementResponse.model_validate(entity)
    if entity.status == AnnouncementStatus.PUBLISHED.value and entity.end_at and entity.end_at < datetime.now():
        resp.is_expired = True
    return resp


@router.post(
    "/",
    summary="创建公告",
    description="创建公告（初始为草稿状态）",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_CREATE.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_CREATE)
def create_announcement(
    body: AnnouncementCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """创建公告接口。

    Args:
        body: 创建请求体
        request: 当前请求对象
        current_user: 当前登录用户（记录操作人）
        service: 公告业务服务

    Returns:
        统一响应结构，data 为新建公告详情
    """
    entity = service.create(
        request=body,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response(_to_response(entity).model_dump(), request)


@router.post(
    "/{announcement_id}/update",
    summary="修改公告",
    description="修改公告信息（所有字段可选）",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_EDIT.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_EDIT)
def update_announcement(
    announcement_id: int,
    body: AnnouncementUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """修改公告接口。

    Args:
        announcement_id: 公告 ID
        body: 修改请求体
        request: 当前请求对象
        current_user: 当前登录用户（记录操作人）
        service: 公告业务服务

    Returns:
        统一响应结构，data 为更新后的公告详情
    """
    entity = service.update(
        announcement_id=announcement_id,
        request=body,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response(_to_response(entity).model_dump(), request)


@router.post(
    "/{announcement_id}/delete",
    summary="删除公告",
    description="删除公告（物理删除）",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_DELETE.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_DELETE)
def delete_announcement(
    announcement_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """删除公告接口。

    Args:
        announcement_id: 公告 ID
        request: 当前请求对象
        current_user: 当前登录用户（记录操作人）
        service: 公告业务服务

    Returns:
        统一响应结构
    """
    service.delete(
        announcement_id=announcement_id,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response({"message": "公告已删除"}, request)


@router.post(
    "/{announcement_id}/publish",
    summary="发布公告",
    description="发布公告（草稿/已下架 → 已发布，校验有效期）",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_PUBLISH.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_PUBLISH)
def publish_announcement(
    announcement_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """发布公告接口。

    Args:
        announcement_id: 公告 ID
        request: 当前请求对象
        current_user: 当前登录用户（记录操作人）
        service: 公告业务服务

    Returns:
        统一响应结构，data 为发布后的公告详情
    """
    entity = service.publish(
        announcement_id=announcement_id,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response(_to_response(entity).model_dump(), request)


@router.post(
    "/{announcement_id}/unpublish",
    summary="下架公告",
    description="下架公告（已发布 → 已下架）",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_PUBLISH.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_PUBLISH)
def unpublish_announcement(
    announcement_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """下架公告接口。

    Args:
        announcement_id: 公告 ID
        request: 当前请求对象
        current_user: 当前登录用户（记录操作人）
        service: 公告业务服务

    Returns:
        统一响应结构，data 为下架后的公告详情
    """
    entity = service.unpublish(
        announcement_id=announcement_id,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response(_to_response(entity).model_dump(), request)


@router.get(
    "/",
    summary="公告列表",
    description="分页查询公告（管理视角，含草稿/已下架）",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_VIEW.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_VIEW)
def list_announcements(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="按发布状态过滤"),
    position: str | None = Query(None, description="按展示位置过滤"),
    keyword: str | None = Query(None, description="按标题/正文关键字搜索"),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """公告列表接口。

    Args:
        request: 当前请求对象
        page: 页码
        page_size: 每页数量
        status: 发布状态过滤
        position: 展示位置过滤
        keyword: 关键字搜索
        service: 公告业务服务

    Returns:
        统一响应结构，data 为分页公告列表
    """
    result = service.list(
        page=page,
        page_size=page_size,
        status=status,
        position=position,
        keyword=keyword,
    )
    items = [_to_response(i).model_dump() for i in result["items"]]
    return success_response(
        PaginatedResponse[AnnouncementResponse](
            items=items,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"],
        ).model_dump(),
        request,
    )


@router.get(
    "/available",
    summary="当前可用的公告列表",
    description="查询当前可用的公告（已发布且在有效期内），供首页板块/横幅展示",
)
def available_announcements(
    request: Request,
    position: str | None = Query(None, description="展示位置过滤（board/banner）"),
    limit: int = Query(20, ge=1, le=50, description="返回条数"),
    _current_user: CurrentUser = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    """首页当前可用公告列表接口（供首页板块/横幅展示，所有登录用户可访问）。

    Args:
        request: 当前请求对象
        position: 展示位置过滤
        limit: 返回条数
        _current_user: 当前登录用户（仅校验登录态）
        service: 公告业务服务

    Returns:
        统一响应结构，data 为可用公告列表
    """
    items = service.list_available(position=position, limit=limit)
    return success_response({"items": [_to_response(i).model_dump() for i in items]}, request)


@router.get(
    "/{announcement_id}",
    summary="公告详情",
    description="查询单条公告详情",
    dependencies=[Depends(require_user_permission(PermissionCode.ANNOUNCEMENT_VIEW.mark))],
)
@permission(PermissionCode.ANNOUNCEMENT_VIEW)
def get_announcement(
    announcement_id: int,
    request: Request,
    service: AnnouncementService = Depends(get_announcement_service),
):
    """公告详情接口。

    Args:
        announcement_id: 公告 ID
        request: 当前请求对象
        service: 公告业务服务

    Returns:
        统一响应结构，data 为公告详情
    """
    entity = service.get(announcement_id)
    return success_response(_to_response(entity).model_dump(), request)


