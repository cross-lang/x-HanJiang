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

from src.api.dependencies import get_request_id, get_user_service
from src.common.response import success, paginated, error
from src.models.user import UserCreateRequest, UserUpdateRequest
from src.service.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", summary="创建用户", description="创建一个新用户")
async def create_user(
    body: UserCreateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """创建用户接口。

    Args:
        body: 用户创建请求数据
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        dict[str, Any]: 标准化成功响应，包含创建的用户数据
    """
    request_id = getattr(request.state, "request_id", None)
    result = service.create(body.model_dump())
    return success(data=result.model_dump(), request_id=request_id)


@router.get("", summary="用户列表", description="查询用户列表（分页）")
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """用户列表接口。

    Args:
        request: FastAPI 请求对象
        page: 页码（从 1 开始）
        page_size: 每页记录数
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        dict[str, Any]: 标准化分页响应
    """
    request_id = getattr(request.state, "request_id", None)
    result = service.get_all(page=page, page_size=page_size)
    items: list[dict] = [item.model_dump() for item in result["items"]]
    return paginated(
        data=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        request_id=request_id,
    )


@router.get("/{user_id}", summary="查询用户", description="根据 ID 查询用户详情")
async def get_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """查询单个用户接口。

    Args:
        user_id: 用户唯一标识
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        dict[str, Any]: 标准化成功响应，包含用户数据
    """
    from src.core.exceptions import NotFoundException

    request_id = getattr(request.state, "request_id", None)
    result = service.get_by_id(user_id)

    if result is None:
        raise NotFoundException(message=f"User with id {user_id} not found")

    return success(data=result.model_dump(), request_id=request_id)


@router.put("/{user_id}", summary="更新用户", description="更新用户信息")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """更新用户接口。

    Args:
        user_id: 用户唯一标识
        body: 用户更新请求数据
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        dict[str, Any]: 标准化成功响应，包含更新后的用户数据
    """
    request_id = getattr(request.state, "request_id", None)
    result = service.update(user_id, body.model_dump(exclude_unset=True))
    return success(data=result.model_dump(), request_id=request_id)


@router.delete("/{user_id}", summary="删除用户", description="根据 ID 删除用户")
async def delete_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """删除用户接口。

    Args:
        user_id: 用户唯一标识
        request: FastAPI 请求对象
        service: 用户业务逻辑实例（DI 自动注入）

    Returns:
        dict[str, Any]: 标准化成功响应
    """
    request_id = getattr(request.state, "request_id", None)
    service.delete(user_id)
    return success(message="User deleted successfully", request_id=request_id)
