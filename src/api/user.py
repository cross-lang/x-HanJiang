#!/usr/bin/env python3
"""
用户接口

本模块提供用户管理的 RESTful API 端点，作为项目三层架构的完整示例。
演示 API 层 → Service 层 → Repository 层的标准调用链路。

Endpoints:
    POST   /users:      创建用户
    GET    /users:      查询用户列表（分页）
    GET    /users/{id}: 查询单个用户
    PUT    /users/{id}: 更新用户信息
    DELETE /users/{id}: 删除用户
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import get_user_service
from src.constants import MSG_SUCCESS
from src.core.exceptions import NotFoundException
from src.schemas.common import ApiResponse, PaginatedResponse
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _success(data: object, request: Request, code: int = 200) -> JSONResponse:
    """构造统一成功响应。"""
    payload = ApiResponse[object](
        code=code,
        message=MSG_SUCCESS,
        data=data,
        timestamp=datetime.now(UTC).isoformat(),
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(exclude_none=False)
    return JSONResponse(status_code=code, content=payload)


@router.post(
    "",
    summary="创建用户",
    description="创建一个新用户",
    status_code=201,
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> JSONResponse:
    """创建用户接口。"""
    result = service.create(body.model_dump())
    return _success(result.model_dump(), request, code=201)


@router.get(
    "",
    summary="用户列表",
    description="查询用户列表（分页）",
)
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(get_user_service),
) -> JSONResponse:
    """用户列表接口。"""
    result = service.get_all(page=page, page_size=page_size)
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
    return _success(page_result.model_dump(), request)


@router.get(
    "/{user_id}",
    summary="查询用户",
    description="根据 ID 查询用户详情",
)
async def get_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> JSONResponse:
    """查询单个用户接口。"""
    result = service.get_by_id(user_id)
    if result is None:
        raise NotFoundException(message=f"User with id {user_id} not found")
    return _success(result.model_dump(), request)


@router.put(
    "/{user_id}",
    summary="更新用户",
    description="更新用户信息",
)
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> JSONResponse:
    """更新用户接口。"""
    result = service.update(user_id, body.model_dump(exclude_unset=True))
    return _success(result.model_dump(), request)


@router.delete(
    "/{user_id}",
    summary="删除用户",
    description="根据 ID 删除用户",
)
async def delete_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> JSONResponse:
    """删除用户接口。"""
    service.delete(user_id)
    return _success({"message": "User deleted successfully"}, request)
