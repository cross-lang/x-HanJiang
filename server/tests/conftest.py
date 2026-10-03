#!/usr/bin/env python3
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


@pytest.fixture(autouse=True)
def _disable_audit_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试环境禁用审计日志写库。

    单元测试使用内存版 Fake Repository 隔离用户数据，但 BaseService._audit
    内部会隐式实例化 AuditService 并连接真实数据库写入 audit_logs，
    导致测试数据污染开发库。此处统一将审计写入降级为 no-op：
        - 开发/生产环境不受影响，审计照常记录；
        - 测试环境不连接真实数据库，符合模板"测试环境隔离"约束。
    """
    monkeypatch.setattr(
        "src.services.admin.audit_service.AuditService.log_event",
        lambda *args, **kwargs: None,
    )


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
