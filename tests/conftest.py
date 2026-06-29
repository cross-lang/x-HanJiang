#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置和 Fixtures

本模块定义了测试环境共用的 pytest fixtures，包括：
    - 测试用 FastAPI 应用实例
    - 测试用 HTTP 客户端
    - 测试环境配置覆盖
"""

import os

import pytest
from fastapi.testclient import TestClient

# 设置测试环境变量（必须在导入 src 模块之前）
os.environ["APP_ENV"] = "testing"


@pytest.fixture
def client() -> TestClient:
    """创建测试用 HTTP 客户端。

    使用 FastAPI TestClient 封装应用实例，支持同步调用异步接口。

    Returns:
        TestClient: 测试用 HTTP 客户端
    """
    from src.main import app

    return TestClient(app)


@pytest.fixture
def app():
    """创建测试用 FastAPI 应用实例。

    Returns:
        FastAPI: 测试用应用实例
    """
    from src.main import app as fastapi_app

    return fastapi_app
