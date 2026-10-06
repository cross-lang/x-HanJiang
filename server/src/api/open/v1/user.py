#!/usr/bin/env python3
"""开放 API 用户管理接口。
将用户管理核心能力暴露给外部服务，通过 AppId/AppKey + scope 鉴权。
operator 上下文记录为调用方应用，而非终端用户。
"""

from fastapi import APIRouter, Depends, Path, Query, Request

from src.api.dependencies import get_user_service
from src.api.open.dependencies import (
    CurrentApp,
    get_app_operator_context,
    get_current_app,
    require_app_scope,
)
from src.api.open.scope_decorator import app_scope
from src.api.response import success_response
from src.constants.enums import UserStatus
from src.constants.scopes import OpenApiScopeCode
from src.schemas.admin.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.schemas.common import ApiResponse, PaginatedResponse
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["开放API：用户管理"])


@router.post(
    "",
    summary="开放 API 创建用户",
    response_model=ApiResponse[UserResponse],
    status_code=201,
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.USER_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.USER_WRITE)
def create_user(
    body: UserCreateRequest,
    request: Request,
    app: CurrentApp = Depends(get_current_app),
    service: UserService = Depends(get_user_service),
):
    """创建用户（需 `user:write` scope）。"""
    result = service.create(body.model_dump(), operator=get_app_operator_context(app))
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "",
    summary="开放 API 用户列表",
    response_model=ApiResponse[PaginatedResponse[UserResponse]],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.USER_READ.mark))],
)
@app_scope(OpenApiScopeCode.USER_READ)
def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页记录数"),
    keyword: str | None = Query(default=None, description="关键字（用户名/姓名/邮箱）"),
    status: UserStatus | None = Query(default=None, description="用户状态过滤"),
    app: CurrentApp = Depends(get_current_app),
    service: UserService = Depends(get_user_service),
):
    """查询用户列表（需 `user:read` scope）。"""
    status_value = status.value if status is not None else None
    result = service.search(keyword=keyword, status=status_value, page=page, page_size=page_size)
    page_result = PaginatedResponse[UserResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"] if result["page_size"] > 0 else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/{user_id}",
    summary="开放 API 用户详情",
    response_model=ApiResponse[UserResponse],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.USER_READ.mark))],
)
@app_scope(OpenApiScopeCode.USER_READ)
def get_user(
    user_id: int = Path(ge=1, description="用户 ID"),
    request: Request = ...,
    app: CurrentApp = Depends(get_current_app),
    service: UserService = Depends(get_user_service),
):
    """查询单个用户详情（需 `user:read` scope）。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(user_id)
    if result is None:
        raise NotFoundException(message=f"用户 {user_id} 不存在")
    return success_response(result.model_dump(), request)


@router.patch(
    "/{user_id}",
    summary="开放 API 更新用户",
    response_model=ApiResponse[UserResponse],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.USER_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.USER_WRITE)
def update_user(
    user_id: int = Path(ge=1, description="用户 ID"),
    body: UserUpdateRequest = ...,
    request: Request = ...,
    app: CurrentApp = Depends(get_current_app),
    service: UserService = Depends(get_user_service),
):
    """更新用户信息（需 `user:write` scope）。"""
    result = service.update(user_id, body.model_dump(exclude_unset=True), operator=get_app_operator_context(app))
    return success_response(result.model_dump(), request)


@router.delete(
    "/{user_id}",
    summary="开放 API 删除用户",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.USER_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.USER_WRITE)
def delete_user(
    user_id: int = Path(ge=1, description="用户 ID"),
    request: Request = ...,
    app: CurrentApp = Depends(get_current_app),
    service: UserService = Depends(get_user_service),
):
    """软删除用户（需 `user:write` scope）。"""
    service.delete(user_id, operator=get_app_operator_context(app))
    return success_response({"deleted": True}, request)
