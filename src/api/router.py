#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中央路由注册模块

本模块负责将所有 API 路由模块统一注册到主路由器上，
采用统一前缀 /api/v1，确保 API 版本化管理。

路由注册顺序：
    1. 健康检查和版本接口
    2. 用户管理接口
    3. （后续新增的业务路由模块）
"""

from fastapi import APIRouter

from src.api import health, user
from src.constants import API_PREFIX

api_router = APIRouter(prefix=API_PREFIX)

# 注册健康检查路由
api_router.include_router(health.router)

# 注册用户管理路由
api_router.include_router(user.router)
