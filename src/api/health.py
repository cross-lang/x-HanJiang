#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查接口

本模块提供应用健康检查和版本信息查询接口，
用于服务监控、负载均衡健康探测和部署验证。

Endpoints:
    GET /health: 健康检查
    GET /version: 版本信息
"""

from fastapi import APIRouter, Request

from src.common.constants import APP_NAME, APP_VERSION
from src.common.response import success
from src.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="健康检查", description="返回服务健康状态信息")
async def health_check(request: Request) -> dict:
    """健康检查接口。

    返回服务当前运行状态、版本号和环境信息。
    用于负载均衡器健康探测和监控系统。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: 标准化健康检查响应
    """
    request_id = getattr(request.state, "request_id", None)
    return success(
        data={
            "status": "ok",
            "app": APP_NAME,
            "version": APP_VERSION,
            "environment": settings.APP_ENV,
        },
        request_id=request_id,
    )


@router.get("/version", summary="版本信息", description="返回应用版本号和 API 版本号")
async def version(request: Request) -> dict:
    """版本信息接口。

    返回应用版本号和 API 版本号。

    Args:
        request: FastAPI 请求对象

    Returns:
        dict: 标准化版本信息响应
    """
    request_id = getattr(request.state, "request_id", None)
    return success(
        data={
            "version": APP_VERSION,
            "api_version": "v1",
        },
        request_id=request_id,
    )
