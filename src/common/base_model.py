#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic 基础模型模块

本模块定义了项目中所有请求/响应模型的公共基类，提供通用字段和校验规则。
所有业务数据模型应继承相应的基类，确保统一的模型规范。

基类列表：
    - BaseRequest: 请求模型基类
    - BaseResponse: 响应模型基类
    - PaginatedRequest: 分页请求基类
    - PaginatedResponse: 分页响应基类
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseRequest(BaseModel):
    """请求模型基类。

    所有 API 请求体模型应继承此类，自动启用 from_attributes 配置。

    Attributes:
        request_id: 请求追踪 ID（可选，由服务端填充）
    """

    request_id: Optional[str] = Field(default=None, description="请求追踪 ID")

    model_config = ConfigDict(from_attributes=True)


class BaseResponse(BaseModel):
    """响应模型基类。

    所有 API 响应数据模型应继承此类。

    Attributes:
        id: 数据唯一标识
        created_at: 创建时间
    """

    id: Optional[int] = Field(default=None, description="数据唯一标识")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class PaginatedRequest(BaseRequest):
    """分页请求基类。

    提供统一的分页参数，所有需要分页的接口应使用此类或其子类。

    Attributes:
        page: 页码（从 1 开始）
        page_size: 每页记录数
    """

    page: int = Field(default=1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(default=20, ge=1, le=100, description="每页记录数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应基类。

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
