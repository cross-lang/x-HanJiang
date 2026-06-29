#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常模块测试

测试异常层级结构、默认错误码、全局异常处理器等功能。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exceptions import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    BusinessException,
    DatabaseException,
    ExternalServiceException,
    NotFoundException,
    SystemException,
    ValidationException,
    register_exception_handlers,
)


class TestExceptionHierarchy:
    """异常层级结构测试。"""

    def test_app_exception_defaults(self):
        """测试 AppException 默认值。"""
        exc = AppException()
        assert exc.code == 500
        assert exc.message == "Application error"

    def test_business_exception_defaults(self):
        """测试 BusinessException 默认值。"""
        exc = BusinessException()
        assert exc.code == 400
        assert isinstance(exc, AppException)

    def test_validation_exception(self):
        """测试 ValidationException。"""
        exc = ValidationException()
        assert exc.code == 422
        assert isinstance(exc, BusinessException)

    def test_authentication_exception(self):
        """测试 AuthenticationException。"""
        exc = AuthenticationException()
        assert exc.code == 401
        assert isinstance(exc, BusinessException)

    def test_authorization_exception(self):
        """测试 AuthorizationException。"""
        exc = AuthorizationException()
        assert exc.code == 403
        assert isinstance(exc, BusinessException)

    def test_not_found_exception(self):
        """测试 NotFoundException。"""
        exc = NotFoundException()
        assert exc.code == 404
        assert isinstance(exc, BusinessException)

    def test_system_exception_defaults(self):
        """测试 SystemException 默认值。"""
        exc = SystemException()
        assert exc.code == 500
        assert isinstance(exc, AppException)

    def test_database_exception(self):
        """测试 DatabaseException。"""
        exc = DatabaseException()
        assert exc.code == 500
        assert isinstance(exc, SystemException)

    def test_external_service_exception(self):
        """测试 ExternalServiceException。"""
        exc = ExternalServiceException()
        assert exc.code == 502
        assert isinstance(exc, SystemException)


class TestExceptionHandlers:
    """全局异常处理器测试。"""

    def _create_test_app(self) -> FastAPI:
        """创建测试用 FastAPI 应用。"""
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/raise-business")
        async def raise_business():
            raise BusinessException(message="test business error", code=400)

        @app.get("/raise-auth")
        async def raise_auth():
            raise AuthenticationException()

        @app.get("/raise-system")
        async def raise_system():
            raise SystemException(message="db down", code=500)

        @app.get("/raise-generic")
        async def raise_generic():
            raise RuntimeError("unexpected error")

        @app.get("/raise-not-found")
        async def raise_not_found():
            raise NotFoundException(message="Item not found")

        return app

    def test_business_exception_handler(self):
        """测试业务异常处理器返回标准化响应。"""
        app = self._create_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/raise-business")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400
        assert data["message"] == "test business error"

    def test_auth_exception_handler(self):
        """测试认证异常处理器。"""
        app = self._create_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/raise-auth")
        assert response.status_code == 401

    def test_system_exception_handler(self):
        """测试系统异常处理器。"""
        app = self._create_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/raise-system")
        assert response.status_code == 500
        data = response.json()
        assert data["code"] == 500

    def test_generic_exception_handler(self):
        """测试通用异常兜底处理器。"""
        app = self._create_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/raise-generic")
        assert response.status_code == 500
        data = response.json()
        assert data["code"] == 500
        assert data["message"] == "Internal server error"

    def test_not_found_exception_handler(self):
        """测试资源未找到异常处理器。"""
        app = self._create_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/raise-not-found")
        assert response.status_code == 404
