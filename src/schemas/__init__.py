#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型层（Schemas）

本目录统一存放接口请求入参、响应返回 Pydantic 模型，
实现 API 层数据结构的标准化定义。

设计原则：
    - 请求模型（*Request）：定义接口入参的字段、类型和校验规则
    - 响应模型（*Response）：定义接口返回的数据结构
    - 数据传输模型（*DTO）：用于层间数据传递
    - 所有模型继承自统一的基类，确保一致的配置

子模块：
    - user: 用户相关的请求/响应模型
    - health: 健康检查相关的响应模型
    - common: 通用模型（分页、错误响应等）
"""

from src.schemas.common import PaginatedRequest, PaginatedResponse, ApiResponse
from src.schemas.health import HealthResponse, VersionResponse
from src.schemas.user import UserCreateRequest, UserUpdateRequest, UserResponse

__all__ = [
    "PaginatedRequest",
    "PaginatedResponse",
    "ApiResponse",
    "HealthResponse",
    "VersionResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
]