#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from typing import Any

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import get_user_service
from src.core.exceptions import NotFoundException
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    summary="创建用户",
    description="创建一个新用户",
    response_model=UserResponse,
    status_code=201,
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """创建用户接口。

    Args:
        body: 用户创建请求数据
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        UserResponse: 创建成功的用户信息
    """
    result = service.create(body.model_dump())
    return result


@router.get(
    "",
    summary="用户列表",
    description="查询用户列表（分页）",
    response_model=PaginatedResponse[UserResponse],
)
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    """用户列表接口。

    Args:
        request: FastAPI 请求对象
        page: 页码（从 1 开始）
        page_size: 每页记录数
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        PaginatedResponse[UserResponse]: 分页响应，包含 items、total、page、page_size
    """
    result = service.get_all(page=page, page_size=page_size)
    return PaginatedResponse(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(result["total"] + result["page_size"] - 1) // result["page_size"] if result["page_size"] > 0 else 0,
    )


@router.get(
    "/{user_id}",
    summary="查询用户",
    description="根据 ID 查询用户详情",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """查询单个用户接口。

    Args:
        user_id: 用户唯一标识
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        UserResponse: 用户信息

    Raises:
        NotFoundException: 用户不存在时抛出
    """
    result = service.get_by_id(user_id)

    if result is None:
        raise NotFoundException(message=f"User with id {user_id} not found")

    return result


@router.put(
    "/{user_id}",
    summary="更新用户",
    description="更新用户信息",
    response_model=UserResponse,
)
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """更新用户接口。

    Args:
        user_id: 用户唯一标识
        body: 用户更新请求数据
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        UserResponse: 更新后的用户信息
    """
    result = service.update(user_id, body.model_dump(exclude_unset=True))
    return result


@router.delete(
    "/{user_id}",
    summary="删除用户",
    description="根据 ID 删除用户",
    response_model=dict[str, str],
)
async def delete_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    """删除用户接口。

    Args:
        user_id: 用户唯一标识
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        dict[str, str]: 删除成功消息
    """
    service.delete(user_id)
    return {"message": "User deleted successfully"}