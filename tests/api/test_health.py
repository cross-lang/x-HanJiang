#!/usr/bin/env python3
"""
健康检查接口测试

测试 /health 和 /version 端点的响应格式和数据。
所有响应统一包装为 {code, message, data, timestamp, request_id}。
"""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """健康检查接口测试。"""

    def test_health_check(self, client: TestClient):
        """测试健康检查接口返回正确的状态信息。"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        body = response.json()
        assert body["code"] == 200
        assert body["message"] == "success"
        assert "data" in body
        assert "timestamp" in body
        assert "request_id" in body

        data = body["data"]
        assert data["status"] in ("ok", "error")
        assert "version" in data
        assert "app" in data
        assert "environment" in data
        assert "database" in data
        assert "cache" in data

    def test_version_endpoint(self, client: TestClient):
        """测试版本信息接口。"""
        response = client.get("/api/v1/version")
        assert response.status_code == 200

        body = response.json()
        assert body["code"] == 200
        data = body["data"]
        assert "version" in data
        assert data["api_version"] == "v1"

    def test_health_has_request_id_header(self, client: TestClient):
        """测试响应头中包含 X-Request-ID。"""
        response = client.get("/api/v1/health")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_response_envelope_shape(self, client: TestClient):
        """所有响应具有标准 envelope 字段。"""
        response = client.get("/api/v1/health")
        body = response.json()
        # 必须存在的标准字段
        for field in ("code", "message", "data", "timestamp", "request_id"):
            assert field in body, f"Missing required field: {field}"
