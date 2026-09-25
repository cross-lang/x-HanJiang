#!/usr/bin/env python3
"""开放平台用户管理接口。

将用户管理核心能力暴露给外部服务，通过 AppId/AppKey + scope 鉴权。
operator 上下文记录为调用方应用，而非终端用户。
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import (
    CurrentApp,
    get_app_operator_context,
    get_current_app,
    get_user_service,
    require_app_scope,
)
from src.api.response import success_response
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["开放平台-用户管理"])


@router.post("", summary="创建用户")
async def create_user(
    body: UserCreateRequest,
    request: Request,
    app: CurrentApp = Depends(require_app_scope("user:write")),
    service: UserService = Depends(get_user_service),
):
    """创建用户（需 `user:write` scope）。"""
    result = service.create(body.model_dump(), operator=get_app_operator_context(app))
    return success_response(result.model_dump(), request, code=201)


@router.get("", summary="用户列表")
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    app: CurrentApp = Depends(require_app_scope("user:read")),
    service: UserService = Depends(get_user_service),
):
    """查询用户列表（需 `user:read` scope）。"""
    result = service.search(keyword=keyword, status=status, page=page, page_size=page_size)
    page_result = PaginatedResponse[UserResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"]
            if result["page_size"] > 0
            else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get("/{user_id}", summary="用户详情")
async def get_user(
    user_id: int,
    request: Request,
    app: CurrentApp = Depends(require_app_scope("user:read")),
    service: UserService = Depends(get_user_service),
):
    """查询单个用户详情（需 `user:read` scope）。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(user_id)
    if result is None:
        raise NotFoundException(message=f"用户 {user_id} 不存在")
    return success_response(result.model_dump(), request)


@router.patch("/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    app: CurrentApp = Depends(require_app_scope("user:write")),
    service: UserService = Depends(get_user_service),
):
    """更新用户信息（需 `user:write` scope）。"""
    result = service.update(
        user_id, body.model_dump(exclude_unset=True), operator=get_app_operator_context(app)
    )
    return success_response(result.model_dump(), request)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    request: Request,
    app: CurrentApp = Depends(require_app_scope("user:write")),
    service: UserService = Depends(get_user_service),
):
    """软删除用户（需 `user:write` scope）。"""
    service.delete(user_id, operator=get_app_operator_context(app))
    return success_response({"deleted": True}, request)
