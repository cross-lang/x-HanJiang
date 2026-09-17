#!/usr/bin/env python3
"""
配置模块测试

测试 Settings 配置加载、环境切换、默认值等功能。
"""




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

    def test_database_and_redis_environment_overrides(self, monkeypatch):
        """测试数据库和 Redis 环境变量覆盖默认配置。"""
        monkeypatch.setenv("MYSQL_HOST", "mysql")
        monkeypatch.setenv("MYSQL_PORT", "3307")
        monkeypatch.setenv("MYSQL_USER", "app")
        monkeypatch.setenv("MYSQL_PASSWORD", "mysql-password")
        monkeypatch.setenv("MYSQL_DATABASE", "app_db")
        monkeypatch.setenv("REDIS_HOST", "redis")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", "redis-password")
        monkeypatch.setenv("REDIS_DB", "2")

        from src.core.config import Settings

        s = Settings()

        assert s.database.host == "mysql"
        assert s.database.port == 3307
        assert s.database.url == "mysql+pymysql://app:mysql-password@mysql:3307/app_db"
        s.database.password = "password with @"
        assert s.database.url == "mysql+pymysql://app:password+with+%40@mysql:3307/app_db"
        assert s.redis.host == "redis"
        assert s.redis.port == 6380
        assert s.redis.db == 2
        assert s.redis.url == "redis://default:redis-password@redis:6380/2"

    def test_local_database_and_redis_environment_overrides(self, monkeypatch):
        """测试本地开发环境使用 MYSQL_*/REDIS_* 配置。"""
        monkeypatch.setenv("MYSQL_HOST", "127.0.0.1")
        monkeypatch.setenv("MYSQL_PORT", "3308")
        monkeypatch.setenv("MYSQL_USER", "local-user")
        monkeypatch.setenv("MYSQL_PASSWORD", "local-password")
        monkeypatch.setenv("MYSQL_DATABASE", "local_db")
        monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
        monkeypatch.setenv("REDIS_PORT", "6381")
        monkeypatch.setenv("REDIS_PASSWORD", "local-redis-password")

        from src.core.config import Settings

        s = Settings()

        assert s.database.url == "mysql+pymysql://local-user:local-password@127.0.0.1:3308/local_db"
        assert s.redis.url == "redis://default:local-redis-password@127.0.0.1:6381/0"

    def test_env_var_generic_loop_coverage(self, monkeypatch):
        """DATABASE_*/REDIS_* env vars correctly override config via generic loop."""
        monkeypatch.setenv("MYSQL_HOST", "prod-mysql")
        monkeypatch.setenv("MYSQL_PORT", "3307")
        monkeypatch.setenv("MYSQL_USER", "prod-user")
        monkeypatch.setenv("MYSQL_PASSWORD", "prod-pass")
        monkeypatch.setenv("MYSQL_DATABASE", "prod_db")
        monkeypatch.setenv("MYSQL_POOL_SIZE", "20")
        monkeypatch.setenv("REDIS_HOST", "prod-redis")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", "redis-pass")

        from src.core.config import Settings

        s = Settings()

        assert s.database.host == "prod-mysql"
        assert s.database.port == 3307
        assert s.database.user == "prod-user"
        assert s.database.password == "prod-pass"
        assert s.database.database == "prod_db"
        assert s.database.pool_size == 20
        assert s.database.url == "mysql+pymysql://prod-user:prod-pass@prod-mysql:3307/prod_db"
        assert s.redis.host == "prod-redis"
        assert s.redis.port == 6380
        assert s.redis.password == "redis-pass"
        assert s.redis.url == "redis://default:redis-pass@prod-redis:6380/0"

    def test_global_singleton(self):
        """测试全局配置单例。"""
        from src.core.config import settings

        assert settings is not None
        assert hasattr(settings, "app_env")
        assert hasattr(settings, "server")

    def test_environment_properties(self):
        """测试环境判断属性。"""
        from src.constants.constants import ENV_DEVELOPMENT
        from src.core.config import Settings

        s = Settings()
        assert s.app_env in (ENV_DEVELOPMENT, "testing")
