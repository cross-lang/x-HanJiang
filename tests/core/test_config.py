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
        assert s.app_env in ("development", "testing")
        assert s.server.host == "0.0.0.0"
        assert s.server.port == 8000
        assert isinstance(s.server.debug, bool)

    def test_logging_config(self):
        """测试日志配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.logging.level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        assert s.logging.file_path
        assert s.logging.rotation
        assert s.logging.retention

    def test_cors_config(self):
        """测试 CORS 配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert isinstance(s.cors.origins, list)
        assert len(s.cors.origins) > 0

    def test_rate_limit_config(self):
        """测试限流配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.rate_limit.per_minute >= 1

    def test_auth_config(self):
        """测试认证配置加载。"""
        from src.core.config import Settings

        s = Settings()
        assert s.auth.secret_key
        assert s.auth.algorithm == "HS256"

    def test_global_singleton(self):
        """测试全局配置单例。"""
        from src.core.config import settings

        assert settings is not None
        assert hasattr(settings, "app_env")
        assert hasattr(settings, "server")

    def test_environment_properties(self):
        """测试环境判断属性。"""
        from src.core.config import Settings
        from src.constants.common import ENV_DEVELOPMENT

        s = Settings()
        assert s.app_env in (ENV_DEVELOPMENT, "testing")