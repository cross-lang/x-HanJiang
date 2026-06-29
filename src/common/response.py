#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化响应格式模块

本模块定义了统一的 API 响应格式，所有接口返回值必须使用本模块的函数构建。
标准响应结构包含：code（状态码）、message（描述信息）、data（数据体）、
timestamp（时间戳）、request_id（请求追踪 ID）。

Usage:
    from src.common.response import success, error, paginated

    # 成功响应
    return success(data={"user": "John"})

    # 错误响应
    return error(code=400, message="Invalid parameter")

    # 分页响应
    return paginated(data=items, total=100, page=1, page_size=20)
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.common.constants import MSG_SUCCESS


class ApiResponse(BaseModel):
    """标准 API 响应模型。

    Attributes:
        code: HTTP 状态码
        message: 响应描述信息
        data: 响应数据体
        timestamp: 响应时间戳（UTC）
        request_id: 请求追踪 ID
    """

    code: int = Field(description="状态码")
    message: str = Field(description="响应描述")
    data: Optional[Any] = Field(default=None, description="响应数据")
    timestamp: str = Field(description="响应时间戳")
    request_id: Optional[str] = Field(default=None, description="请求追踪 ID")

    model_config = {"from_attributes": True}


def success(
    data: Optional[Any] = None,
    message: str = MSG_SUCCESS,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    """构建成功响应。

    Args:
        data: 响应数据体
        message: 成功描述信息（默认 "success"）
        request_id: 请求追踪 ID

    Returns:
        dict[str, Any]: 标准化成功响应字典
    """
    return ApiResponse(
        code=200,
        message=message,
        data=data,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
    ).model_dump(mode="json")


def error(
    code: int,
    message: str,
    request_id: Optional[str] = None,
    data: Optional[Any] = None,
) -> dict[str, Any]:
    """构建错误响应。

    Args:
        code: HTTP 错误状态码
        message: 错误描述信息
        request_id: 请求追踪 ID
        data: 附加数据（如错误详情）

    Returns:
        dict[str, Any]: 标准化错误响应字典
    """
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
    ).model_dump(mode="json")


def paginated(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = MSG_SUCCESS,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    """构建分页响应。

    Args:
        data: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页记录数
        message: 响应描述信息
        request_id: 请求追踪 ID

    Returns:
        dict[str, Any]: 包含分页信息的标准化响应字典
    """
    response: dict[str, Any] = success(data=data, message=message, request_id=request_id)
    response["pagination"] = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }
    return response
