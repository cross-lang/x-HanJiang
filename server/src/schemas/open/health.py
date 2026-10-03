#!/usr/bin/env python3
"""开放平台健康/版本接口响应模型。"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """开放平台健康检查响应。"""

    status: str = Field(description="服务状态，如 ok")
    service: str = Field(description="服务标识，固定为 openapi")
    app: str = Field(description="应用名称")


class VersionResponse(BaseModel):
    """开放平台版本信息响应。"""

    app_version: str = Field(description="应用版本号")
    api_version: str = Field(description="开放平台 API 版本号，如 v1")
