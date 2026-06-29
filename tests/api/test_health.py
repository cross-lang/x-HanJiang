#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查接口测试

测试 /health 和 /version 端点的响应格式和数据。
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """健康检查接口测试。"""

    def test_health_check(self, client: TestClient):
        """测试健康检查接口返回正确的状态信息。"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "success"
        assert data["data"]["status"] == "ok"
        assert "version" in data["data"]
        assert "app" in data["data"]
        assert "request_id" in data

    def test_version_endpoint(self, client: TestClient):
        """测试版本信息接口。"""
        response = client.get("/api/v1/version")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "success"
        assert "version" in data["data"]
        assert data["data"]["api_version"] == "v1"

    def test_health_has_request_id_header(self, client: TestClient):
        """测试响应头中包含 X-Request-ID。"""
        response = client.get("/api/v1/health")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_health_response_timestamp(self, client: TestClient):
        """测试响应包含时间戳。"""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "timestamp" in data
