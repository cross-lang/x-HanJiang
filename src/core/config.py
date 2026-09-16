#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置管理

支持从环境变量和 YAML 配置文件读取配置，使用 dataclass 描述各配置段。
配置优先级：环境变量 > 环境特定配置(config.{env}.yaml) > 默认配置(config.yaml) > 代码默认值。

Usage:
    from src.core.config import settings
    port = settings.server.port
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import yaml

from src.constants import (
    DEFAULT_CONFIG_DIR,
    ENV_DEVELOPMENT,
    ENV_PRODUCTION,
    ENV_TESTING,
)


# ============================================================
# 辅助函数
# ============================================================

def _to_bool(value: str | None) -> bool:
    """将字符串转换为布尔值。"""
    return value.lower() == "true" if value else False


def _to_int(value: str | None, default: int = 0) -> int:
    """将字符串转换为整数。"""
    return int(value) if value else default


def _to_float(value: str | None, default: float = 0.0) -> float:
    """将字符串转换为浮点数。"""
    return float(value) if value else default


def _find_project_root() -> Path:
    """向上查找项目根目录（包含 pyproject.toml 的目录）。"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parent.parent


# ============================================================
# 明确禁止使用的弱密钥
# ============================================================

_FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "change-me-in-production",
        "change-me",
        "secret",
        "default",
        "changeme",
        "dev-only-change-me-in-production",
        "",
    }
)


# ============================================================
# Dataclass 配置段
# ============================================================

@dataclass
class ServerConfig:
    """服务器配置。"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    workers: int = 1


@dataclass
class LoggingConfig:
    """日志配置。

    format:
        "json"    — 结构化 JSON 日志，适合 Loki / ELK 收集（生产默认）
        "console" — 彩色人可读格式，适合本地开发
    """
    level: str = "INFO"
    format: str = "json"
    file_path: str = "logs/x-HanJiang-{time:YYYYMMDDHH}.log"
    rotation: str = "1 day"
    retention: str = "7 days"
    compression: str = "zip"
    console_output: bool = True


@dataclass
class CORSConfig:
    """跨域配置。"""
    enabled: bool = True
    origins: list[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class RateLimitConfig:
    """限流配置。"""
    enabled: bool = True
    per_minute: int = 60
    per_hour: int = 1000


@dataclass
class AuthConfig:
    """认证 / JWT 配置。"""
    secret_key: str = "dev-only-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    refresh_token_expire_days: int = 30


@dataclass
class DatabaseConfig:
    """数据库配置。"""
    enabled: bool = True
    url: str = "mysql://root:CHANGE_ME@localhost:3306/hanjiang"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis 配置。"""
    enabled: bool = True
    url: str = "redis://:CHANGE_ME@localhost:6379/0"
    pool_size: int = 10
    max_connections: int = 50
    decode_responses: bool = True
    socket_timeout: int = 5


@dataclass
class LocalStorageConfig:
    """本地文件存储配置。"""
    base_dir: str = "static"


@dataclass
class S3StorageConfig:
    """S3 兼容存储配置（七牛 Kodo S3 API / AWS S3 / MinIO 等）。

    通过 endpoint_url 指定 S3 兼容服务地址，region 使用标准 S3 区域标识。
    七牛 Kodo S3 兼容 endpoint 格式：https://s3.<region>.qiniucs.com
    """
    endpoint_url: str = ""
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "x-hanjiang"
    region: str = "cn-south-1"
    prefix: str = "uploads"
    public_url: str = ""
    use_ssl: bool = True


@dataclass
class StorageConfig:
    """统一存储配置。

    provider: "local" | "s3"
        - local:  本地文件系统（开发环境默认）
        - s3:     S3 兼容对象存储（七牛 Kodo / AWS S3 / MinIO，生产环境推荐）
    """
    provider: str = "local"
    local: LocalStorageConfig = field(default_factory=LocalStorageConfig)
    s3: S3StorageConfig = field(default_factory=S3StorageConfig)


@dataclass
class SmtpConfig:
    """SMTP 邮件服务器配置。"""
    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_name: str = "HanJiang"
    from_address: str = ""


@dataclass
class PasswordResetConfig:
    """密码重置配置。"""
    token_expire_minutes: int = 15
    max_attempts_per_hour: int = 5
    frontend_url: str = "http://localhost:3000"


# ============================================================
# 环境变量 → YAML 配置段 映射
# ============================================================

_ENV_SECTION_MAP: dict[str, tuple[str, list[str]]] = {
    "server": ("SERVER_", ["host", "port", "debug", "workers"]),
    "logging": ("LOGGING_", ["level", "format", "file_path", "rotation", "retention", "compression", "console_output"]),
    "cors": ("CORS_", ["enabled", "origins", "allow_credentials", "allow_methods", "allow_headers"]),
    "rate_limit": ("RATE_LIMIT_", ["enabled", "per_minute", "per_hour"]),
    "auth": ("AUTH_", ["secret_key", "algorithm", "access_token_expire_minutes", "refresh_token_expire_days"]),
    "database": ("DATABASE_", ["enabled", "url", "pool_size", "max_overflow", "pool_timeout", "pool_recycle", "echo"]),
    "redis": ("REDIS_", ["enabled", "url", "pool_size", "max_connections", "decode_responses", "socket_timeout"]),
    "storage": ("STORAGE_", ["provider"]),
    "smtp": ("SMTP_", ["host", "port", "username", "password", "use_tls", "from_name", "from_address"]),
    "password_reset": ("PASSWORD_RESET_", ["token_expire_minutes", "max_attempts_per_hour", "frontend_url"]),
}


# ============================================================
# 核心配置类
# ============================================================

class Settings:
    """应用全局配置类。

    配置加载优先级（从高到低）：
        1. 环境变量
        2. 环境特定 YAML 配置（config.{env}.yaml）
        3. 默认 YAML 配置（config.yaml）
        4. 代码中的默认值

    Attributes:
        app_env: 当前运行环境
        server: 服务器配置
        logging: 日志配置
        cors: 跨域配置
        rate_limit: 限流配置
        auth: 认证配置
        database: 数据库配置
        redis: Redis 配置
        storage: 统一存储配置
    """

    def __init__(self) -> None:
        """初始化配置。"""
        self._config: dict[str, Any] = self._load_config()
        self._parse_config()

    # ----------------------------------------------------------
    # 配置加载
    # ----------------------------------------------------------

    def _load_config(self) -> dict[str, Any]:
        """加载配置，优先级：环境变量 > YAML 文件 > 默认值。"""
        config = self._get_default_config()
        self._load_from_yaml(config)
        self._load_from_env(config)
        return config

    def _get_default_config(self) -> dict[str, Any]:
        """返回所有配置段的代码默认值。"""
        return {
            "app_env": ENV_DEVELOPMENT,
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "workers": 1,
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file_path": "logs/x-HanJiang-{time:YYYYMMDDHH}.log",
                "rotation": "1 day",
                "retention": "7 days",
                "compression": "zip",
                "console_output": True,
            },
            "cors": {
                "enabled": True,
                "origins": ["*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            },
            "rate_limit": {
                "enabled": True,
                "per_minute": 60,
                "per_hour": 1000,
            },
            "auth": {
                "secret_key": "dev-only-change-me-in-production",
                "algorithm": "HS256",
                "access_token_expire_minutes": 10080,
                "refresh_token_expire_days": 30,
            },
            "database": {
                "enabled": True,
                "url": "mysql://root:CHANGE_ME@localhost:3306/hanjiang",
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "echo": False,
            },
            "redis": {
                "enabled": True,
                "url": "redis://:CHANGE_ME@localhost:6379/0",
                "pool_size": 10,
                "max_connections": 50,
                "decode_responses": True,
                "socket_timeout": 5,
            },
            "storage": {
                "provider": "local",
                "local": {
                    "base_dir": "static",
                },
                "s3": {
                    "endpoint_url": "",
                    "access_key": "",
                    "secret_key": "",
                    "bucket": "x-hanjiang",
                    "region": "cn-south-1",
                    "prefix": "uploads",
                    "public_url": "",
                    "use_ssl": True,
                },
            },
            "smtp": {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "",
                "password": "",
                "use_tls": True,
                "from_name": "HanJiang",
                "from_address": "",
            },
            "password_reset": {
                "token_expire_minutes": 15,
                "max_attempts_per_hour": 5,
                "frontend_url": "http://localhost:3000",
            },
        }

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """递归合并配置字典，override 中的值覆盖 base 中的同名键。"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _load_from_yaml(self, config: dict[str, Any]) -> None:
        """从 YAML 文件加载配置。

        先加载默认 config.yaml，再加载 config.{env}.yaml 进行深度覆盖。
        """
        project_root = _find_project_root()
        config_dir = project_root / DEFAULT_CONFIG_DIR

        # 1. 加载默认配置
        default_file = config_dir / "config.yaml"
        if default_file.exists():
            try:
                with open(default_file, encoding="utf-8") as f:
                    default_cfg = yaml.safe_load(f) or {}
                if isinstance(default_cfg, dict):
                    self._merge_config(config, default_cfg)
            except Exception as e:
                print(f"Warning: Cannot load config file {default_file}: {e}")

        # 2. 加载环境特定配置（覆盖默认配置）
        app_env = os.environ.get("APP_ENV", config.get("app_env", ENV_DEVELOPMENT))
        env_file = config_dir / f"config.{app_env}.yaml"
        if env_file.exists():
            try:
                with open(env_file, encoding="utf-8") as f:
                    env_cfg = yaml.safe_load(f) or {}
                if isinstance(env_cfg, dict):
                    self._merge_config(config, env_cfg)
            except Exception as e:
                print(f"Warning: Cannot load config file {env_file}: {e}")

        env_dot_file = project_root / ".env"
        if env_dot_file.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_dot_file, override=False)
            except Exception as e:
                print(f"Warning: Cannot load .env file {env_dot_file}: {e}")

    def _load_from_env(self, config: dict[str, Any]) -> None:
        """从环境变量加载配置，覆盖 YAML 和默认值。

        映射规则：
            APP_ENV       → app_env
            SERVER_HOST   → server.host
            DATABASE_URL  → database.url
            … 以此类推
        """
        # 顶层 app_env
        if value := os.environ.get("APP_ENV"):
            config["app_env"] = value

        # 各配置段
        for section_name, (prefix, keys) in _ENV_SECTION_MAP.items():
            if section_name not in config:
                continue
            section = config[section_name]
            for key in keys:
                env_key = f"{prefix}{key.upper()}"
                value = os.environ.get(env_key)
                if value is None:
                    continue
                # 根据默认值类型进行转换
                default_val = section.get(key)
                if isinstance(default_val, bool):
                    section[key] = _to_bool(value)
                elif isinstance(default_val, int):
                    section[key] = _to_int(value)
                elif isinstance(default_val, float):
                    section[key] = _to_float(value)
                elif isinstance(default_val, list):
                    section[key] = [v.strip() for v in value.split(",")]
                else:
                    section[key] = value

        # 嵌套存储配置的环境变量
        storage = config.setdefault("storage", {})
        storage_local = storage.setdefault("local", {})
        storage_s3 = storage.setdefault("s3", {})

        if value := os.environ.get("STORAGE_LOCAL_BASE_DIR"):
            storage_local["base_dir"] = value
        if value := os.environ.get("STORAGE_S3_ENDPOINT_URL"):
            storage_s3["endpoint_url"] = value
        if value := os.environ.get("STORAGE_S3_ACCESS_KEY"):
            storage_s3["access_key"] = value
        if value := os.environ.get("STORAGE_S3_SECRET_KEY"):
            storage_s3["secret_key"] = value
        if value := os.environ.get("STORAGE_S3_BUCKET"):
            storage_s3["bucket"] = value
        if value := os.environ.get("STORAGE_S3_REGION"):
            storage_s3["region"] = value
        if value := os.environ.get("STORAGE_S3_PREFIX"):
            storage_s3["prefix"] = value
        if value := os.environ.get("STORAGE_S3_PUBLIC_URL"):
            storage_s3["public_url"] = value
        if value := os.environ.get("STORAGE_S3_USE_SSL"):
            storage_s3["use_ssl"] = _to_bool(value)

        # SMTP 邮件配置的环境变量
        smtp = config.setdefault("smtp", {})
        if value := os.environ.get("SMTP_HOST"):
            smtp["host"] = value
        if value := os.environ.get("SMTP_PORT"):
            smtp["port"] = _to_int(value, 587)
        if value := os.environ.get("SMTP_USERNAME"):
            smtp["username"] = value
        if value := os.environ.get("SMTP_PASSWORD"):
            smtp["password"] = value
        if value := os.environ.get("SMTP_USE_TLS"):
            smtp["use_tls"] = _to_bool(value)
        if value := os.environ.get("SMTP_FROM_NAME"):
            smtp["from_name"] = value
        if value := os.environ.get("SMTP_FROM_ADDRESS"):
            smtp["from_address"] = value

        # 密码重置配置的环境变量
        password_reset = config.setdefault("password_reset", {})
        if value := os.environ.get("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES"):
            password_reset["token_expire_minutes"] = _to_int(value, 15)
        if value := os.environ.get("PASSWORD_RESET_MAX_ATTEMPTS_PER_HOUR"):
            password_reset["max_attempts_per_hour"] = _to_int(value, 5)
        if value := os.environ.get("PASSWORD_RESET_FRONTEND_URL"):
            password_reset["frontend_url"] = value

    # ----------------------------------------------------------
    # 解析到 dataclass
    # ----------------------------------------------------------

    def _parse_config(self) -> None:
        """将原始配置字典解析为 dataclass 实例。"""
        self.app_env: str = self._config.get("app_env", ENV_DEVELOPMENT)

        self.server = ServerConfig(**self._config.get("server", {}))
        self.logging = LoggingConfig(**self._config.get("logging", {}))
        self.cors = CORSConfig(**self._config.get("cors", {}))
        self.rate_limit = RateLimitConfig(**self._config.get("rate_limit", {}))
        self.auth = AuthConfig(**self._config.get("auth", {}))
        self.database = DatabaseConfig(**self._config.get("database", {}))
        self.redis = RedisConfig(**self._config.get("redis", {}))

        # 存储抽象层配置（嵌套 dataclass）
        storage_raw = self._config.get("storage", {})
        local_raw = storage_raw.pop("local", {})
        s3_raw = storage_raw.pop("s3", {})
        self.storage = StorageConfig(
            provider=storage_raw.get("provider", "local"),
            local=LocalStorageConfig(**local_raw),
            s3=S3StorageConfig(**s3_raw),
        )

        # SMTP 邮件配置
        smtp_raw = self._config.get("smtp", {})
        self.smtp = SmtpConfig(**smtp_raw)

        # 密码重置配置
        password_reset_raw = self._config.get("password_reset", {})
        self.password_reset = PasswordResetConfig(**password_reset_raw)

    # ----------------------------------------------------------
    # 环境判断
    # ----------------------------------------------------------

    @property
    def is_development(self) -> bool:
        """是否为开发环境。"""
        return self.app_env == ENV_DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """是否为测试环境。"""
        return self.app_env == ENV_TESTING

    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.app_env == ENV_PRODUCTION

    # ----------------------------------------------------------
    # 配置校验
    # ----------------------------------------------------------

    def validate(self) -> None:
        """验证配置合法性，配置错误直接阻断程序启动。

        生产环境额外校验：
            - 调试模式必须关闭
            - AUTH_SECRET_KEY 不能是占位符，且长度 ≥ 32
            - CORS origins 不能为 '*'
            - 数据库与 Redis 必须显式配置

        Raises:
            ValueError: 配置不合法时抛出
        """
        # 通用校验：密钥最小长度
        if len(self.auth.secret_key) < 16:
            raise ValueError("AUTH_SECRET_KEY 长度至少 16 个字符")

        if self.is_production:
            if self.server.debug:
                raise ValueError("DEBUG mode must be disabled in production")

            key = self.auth.secret_key
            if (
                key.lower() in _FORBIDDEN_SECRET_KEYS
                or key.startswith("dev-only-")
                or len(key) < 32
            ):
                raise ValueError(
                    "AUTH_SECRET_KEY 在生产环境必须配置为至少 32 字符的随机字符串，"
                    "可通过 `python -c \"from src.core.security import "
                    "generate_secret_key; print(generate_secret_key())\"` 生成"
                )

            if "*" in self.cors.origins:
                raise ValueError(
                    "CORS origins 在生产环境禁止配置为 '*'，请指定可信来源列表"
                )

            if not self.database.url:
                raise ValueError("DATABASE_URL 在生产环境必须配置")

            if not self.redis.url:
                raise ValueError("REDIS_URL 在生产环境必须配置")

        # 数据库协议校验
        if self.database.url and not self.database.url.startswith(
            ("mysql://", "mysql+pymysql://", "postgresql://", "sqlite://")
        ):
            raise ValueError(
                "Unsupported database type, only MySQL, PostgreSQL and SQLite are supported"
            )

    # ----------------------------------------------------------
    # 热重载
    # ----------------------------------------------------------

    def reload(self) -> None:
        """重新加载全部配置（YAML + 环境变量），并重新校验。"""
        self._config = self._load_config()
        self._parse_config()
        self.validate()


# ============================================================
# 全局单例
# ============================================================

settings: Final[Settings] = Settings()
settings.validate()
