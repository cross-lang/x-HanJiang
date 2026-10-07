#!/usr/bin/env python3
"""
数据模型层（Schemas）
本目录统一存放接口请求入参、响应返回 Pydantic 模型，
实现 API 层数据结构的标准化定义。
设计原则：
    - 请求模型（*Request）：定义接口入参的字段、类型和校验规则
    - 响应模型（*Response）：定义接口返回的数据结构
    - 数据传输模型（*DTO）：用于层间数据传递
    - 所有模型继承自统一的基类，确保一致的配置
子模块（按域划分，对应 api/services 三层）：
    - user / role（根目录）：用户、角色/权限双渠道共享 DTO（管理端与开放接口共用）
    - admin：管理系统渠道特有 DTO（通知/应用管理/健康检查等）
    - open：开放接口（网关）DTO（调用方应用身份 CurrentApp、告警推送）
    - open_portal：开放平台门户 DTO（开发者账号/资料/应用）
    - common（根目录）：公共模型（分页、统一响应包裹等）
"""

from src.schemas.admin.assistant import (
    ChatRequest,
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
)
from src.schemas.admin.health import HealthResponse, VersionResponse
from src.schemas.common import ApiResponse, PaginatedRequest, PaginatedResponse
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest

__all__ = [
    "PaginatedRequest",
    "PaginatedResponse",
    "ApiResponse",
    "HealthResponse",
    "VersionResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
    "ChatRequest",
    "ConversationResponse",
    "FeedbackRequest",
    "MessageResponse",
]
