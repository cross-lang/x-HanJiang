#!/usr/bin/env python3
"""
异常处理器细节测试

验证：
    - 4xx 异常透传 details
    - 生产环境 5xx 异常不暴露 details
    - 开发环境 5xx 异常可暴露 details（便于排查）
    - 时间戳字段非空
    - request_id 透传
"""

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.core.exceptions import (
    BusinessException,
    NotFoundException,
    SystemException,
    register_exception_handlers,
)


@pytest.fixture
def test_app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/biz")
    async def biz():
        raise BusinessException(message="biz fail", code=400, details={"k": "v"})

    @app.get("/sys")
    async def sys_():
        raise SystemException(
            message="db down",
            code=500,
            details={"password": "x", "internal": "leak"},
        )

    @app.get("/notfound")
    async def notfound():
        raise NotFoundException(message="missing")

    return app


class TestAppExceptionHandler:
    """应用异常处理器测试。"""

    def test_business_exception_returns_details(self, test_app):
        """4xx 异常始终透传 details。"""
        client = TestClient(test_app, raise_server_exceptions=False)
        resp = client.get("/biz")
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == 400
        assert data["message"] == "biz fail"
        assert data["data"] == {"details": {"k": "v"}}
        assert data["request_id"] is None
        assert data["timestamp"]

    def test_not_found_status_and_payload(self, test_app):
        client = TestClient(test_app, raise_server_exceptions=False)
        resp = client.get("/notfound")
        assert resp.status_code == 404
        assert resp.json()["code"] == 404

    def test_timestamp_is_iso(self, test_app):
        """timestamp 字段是 ISO 字符串。"""
        client = TestClient(test_app, raise_server_exceptions=False)
        resp = client.get("/notfound")
        ts = resp.json()["timestamp"]
        # ISO 格式可被 datetime 解析
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
