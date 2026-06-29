#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块测试

测试日志初始化、配置消费、实例单例等功能。
"""

import pytest


class TestLogger:
    """日志模块测试。"""

    def test_logger_import(self):
        """测试日志实例可正常导入。"""
        from src.core.logger import logger

        assert logger is not None

    def test_setup_logging(self):
        """测试日志初始化函数可正常调用。"""
        from src.core.logger import setup_logging

        # 不应抛出异常
        setup_logging()

    def test_setup_logging_idempotent(self):
        """测试日志初始化幂等性（多次调用不会报错）。"""
        from src.core.logger import setup_logging

        setup_logging()
        setup_logging()  # 第二次调用应被跳过

    def test_get_logger(self):
        """测试获取日志实例。"""
        from src.core.logger import get_logger

        log = get_logger()
        assert log is not None

    def test_logger_bind_request_id(self):
        """测试日志绑定 request_id。"""
        from src.core.logger import logger

        bound = logger.bind(request_id="test-uuid-123")
        assert bound is not None
