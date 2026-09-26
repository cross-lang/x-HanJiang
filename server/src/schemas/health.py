#!/usr/bin/env python3
"""
健康检查数据模型

本模块定义了健康检查接口的请求和响应数据模型。

Classes:
    HealthResponse: 健康检查响应模型
    VersionResponse: 版本信息响应模型
"""


from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """健康检查响应模型。

    Attributes:
        status: 服务状态（"ok" 表示正常，"error" 表示异常）
        version: 应用版本号
        app: 应用名称
        environment: 运行环境
        database: 数据库连接状态
        cache: 缓存连接状态
    """

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(description="应用版本号")
    app: str = Field(description="应用名称")
    environment: str = Field(description="运行环境")
    database: str | None = Field(default=None, description="数据库连接状态")
    cache: str | None = Field(default=None, description="缓存连接状态")


class VersionResponse(BaseModel):
    """版本信息响应模型。

    Attributes:
        version: 应用版本号
        api_version: API 版本号（如 "v1"），与路由前缀一致
    """

    version: str = Field(description="应用版本号")
    api_version: str = Field(default="v1", description="API 版本号")

    @classmethod
    def current(cls) -> "VersionResponse":
        """构造当前版本响应。

        health 接口挂在用户态 v1 路由下，api_version 固定为 v1；
        开放平台有自己的版本号，不在此响应范围内。
        """
        from src.constants import APP_VERSION

        return cls(version=APP_VERSION, api_version="v1")
