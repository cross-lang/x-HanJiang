#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查数据模型

本模块定义了健康检查接口的响应数据模型。

Classes:
    HealthResponse: 健康检查响应模型
    VersionResponse: 版本信息响应模型
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查响应模型。

    Attributes:
        status: 服务状态（"ok" 表示正常）
        version: 应用版本号
        app: 应用名称
        environment: 运行环境
    """

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(description="应用版本号")
    app: str = Field(description="应用名称")
    environment: str = Field(description="运行环境")

    model_config = {"from_attributes": True}


class VersionResponse(BaseModel):
    """版本信息响应模型。

    Attributes:
        version: 应用版本号
        api_version: API 版本号
    """

    version: str = Field(description="应用版本号")
    api_version: str = Field(default="v1", description="API 版本号")

    model_config = {"from_attributes": True}
