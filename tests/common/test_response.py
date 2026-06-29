#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化响应格式测试

测试 success/error/paginated 响应构建函数。
"""

import pytest

from src.common.response import success, error, paginated


class TestSuccessResponse:
    """成功响应测试。"""

    def test_success_default(self):
        """测试默认成功响应。"""
        result = success()
        assert result["code"] == 200
        assert result["message"] == "success"
        assert result["data"] is None
        assert "timestamp" in result

    def test_success_with_data(self):
        """测试带数据的成功响应。"""
        data = {"name": "John", "age": 28}
        result = success(data=data)
        assert result["code"] == 200
        assert result["data"] == data

    def test_success_with_request_id(self):
        """测试带 request_id 的成功响应。"""
        result = success(request_id="test-uuid-123")
        assert result["request_id"] == "test-uuid-123"

    def test_success_custom_message(self):
        """测试自定义消息的成功响应。"""
        result = success(message="Operation completed")
        assert result["message"] == "Operation completed"


class TestErrorResponse:
    """错误响应测试。"""

    def test_error_basic(self):
        """测试基本错误响应。"""
        result = error(code=400, message="Bad request")
        assert result["code"] == 400
        assert result["message"] == "Bad request"
        assert result["data"] is None

    def test_error_with_request_id(self):
        """测试带 request_id 的错误响应。"""
        result = error(code=500, message="Server error", request_id="test-uuid")
        assert result["request_id"] == "test-uuid"

    def test_error_404(self):
        """测试 404 错误响应。"""
        result = error(code=404, message="Not found")
        assert result["code"] == 404

    def test_error_with_data(self):
        """测试带附加数据的错误响应。"""
        result = error(code=422, message="Validation error", data={"field": "email"})
        assert result["data"] == {"field": "email"}


class TestPaginatedResponse:
    """分页响应测试。"""

    def test_paginated_basic(self):
        """测试基本分页响应。"""
        items = [{"id": 1}, {"id": 2}]
        result = paginated(data=items, total=100, page=1, page_size=20)

        assert result["code"] == 200
        assert result["data"] == items
        assert result["pagination"]["total"] == 100
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 20

    def test_paginated_total_pages(self):
        """测试总页数计算。"""
        result = paginated(data=[], total=50, page=1, page_size=20)
        assert result["pagination"]["total_pages"] == 3

    def test_paginated_empty(self):
        """测试空数据分页响应。"""
        result = paginated(data=[], total=0, page=1, page_size=20)
        assert result["data"] == []
        assert result["pagination"]["total"] == 0

    def test_paginated_with_request_id(self):
        """测试带 request_id 的分页响应。"""
        result = paginated(
            data=[], total=0, page=1, page_size=20, request_id="test-uuid"
        )
        assert result["request_id"] == "test-uuid"
