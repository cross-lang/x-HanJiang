#!/usr/bin/env python3
"""
中间件测试

测试 RequestIDMiddleware / RequestLoggingMiddleware 的行为：
    - RequestIDMiddleware 应生成或透传 X-Request-ID
    - RequestLoggingMiddleware 不应破坏 body 流（下游 endpoint 仍能解析）
    - 敏感请求头在日志中被脱敏
"""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.core.middleware import RequestIDMiddleware, RequestLoggingMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/echo")
    async def echo(body: dict[str, Any]):
        return {"received": body}

    @app.get("/hello")
    async def hello():
        return {"hello": "world"}

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    return app


class TestRequestIDMiddleware:
    """RequestIDMiddleware 测试。"""

    def test_generates_request_id_when_missing(self):
        app = _build_app()
        client = TestClient(app)
        resp = client.get("/hello")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    def test_reuses_inbound_request_id(self):
        app = _build_app()
        client = TestClient(app)
        inbound = "test-inbound-uuid-123"
        resp = client.get("/hello", headers={"X-Request-ID": inbound})
        assert resp.headers["x-request-id"] == inbound


class TestRequestLoggingMiddleware:
    """RequestLoggingMiddleware 测试。"""

    def test_body_still_readable_downstream(self):
        """中间件读取 body 用于日志不应破坏下游解析。"""
        app = _build_app()
        client = TestClient(app)
        payload = {"username": "alice", "email": "a@b.com"}
        resp = client.post("/echo", json=payload)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"received": payload}

    def test_logs_run_without_error(self):
        """中间件完整生命周期不应抛错。"""
        app = _build_app()
        client = TestClient(app)
        # 同时带敏感头，确保脱敏代码路径也执行
        resp = client.get(
            "/hello",
            headers={
                "Authorization": "Bearer secret-token",
                "Cookie": "session=abc",
            },
        )
        assert resp.status_code == 200
