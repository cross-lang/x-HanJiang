#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用数据模型

本模块定义了项目中所有请求/响应模型的公共基类和通用数据结构，
提供通用字段和校验规则。

基类列表：
    - ApiResponse: 标准 API 响应模型
    - PaginatedRequest: 分页请求模型
    - PaginatedResponse: 分页响应模型
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


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

    model_config = ConfigDict(from_attributes=True)


class PaginatedRequest(BaseModel):
    """分页请求模型。

    提供统一的分页参数，所有需要分页的接口应使用此类。

    Attributes:
        page: 页码（从 1 开始）
        page_size: 每页记录数
    """

    page: int = Field(default=1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页记录数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型。

    提供统一的分页元数据，与数据列表配合使用。

    Attributes:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页记录数
        total_pages: 总页数
    """

    items: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, ge=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, description="每页记录数")
    total_pages: int = Field(default=0, ge=0, description="总页数")

    model_config = ConfigDict(from_attributes=True)