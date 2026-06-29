#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块测试

测试 Settings 配置加载、环境切换、默认值等功能。
"""

import os

import pytest


class TestSettings:
    """Settings 配置类测试。"""

    def test_default_config_values(self):
        """测试默认配置值是否正确加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.APP_ENV in ("development", "testing")
        assert s.server.SERVER_HOST == "0.0.0.0"
        assert s.server.SERVER_PORT == 8000
        assert isinstance(s.server.SERVER_DEBUG, bool)

    def test_logging_config(self):
        """测试日志配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.logging.LOGGING_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        assert s.logging.LOGGING_FILE_PATH
        assert s.logging.LOGGING_ROTATION
        assert s.logging.LOGGING_RETENTION

    def test_cors_config(self):
        """测试 CORS 配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert isinstance(s.cors.CORS_ORIGINS, list)
        assert len(s.cors.CORS_ORIGINS) > 0

    def test_rate_limit_config(self):
        """测试限流配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.rate_limit.RATE_LIMIT_PER_MINUTE >= 1

    def test_auth_config(self):
        """测试认证配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.auth.AUTH_SECRET_KEY
        assert s.auth.AUTH_ALGORITHM == "HS256"

    def test_global_singleton(self):
        """测试全局配置单例。"""
        from src.core.config import settings

        assert settings is not None
        assert hasattr(settings, "APP_ENV")
        assert hasattr(settings, "server")

    def test_environment_properties(self):
        """测试环境判断属性。"""
        from src.core.config import Settings
        from src.common.constants import ENV_DEVELOPMENT

        s = Settings()
        # 默认应为开发或测试环境
        assert s.APP_ENV in (ENV_DEVELOPMENT, "testing")
