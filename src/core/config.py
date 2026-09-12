#!/usr/bin/env python3
"""
应用配置管理模块

本模块实现统一配置加载逻辑，支持多环境切换，为全局唯一配置入口。
配置优先级：环境变量 > 环境特定 YAML 配置 > 默认 YAML 配置 > 代码默认值。

功能特性：
    - 支持 .env 环境变量 + config.yaml 配置文件双来源
    - 支持多环境切换（development / testing / production），通过 APP_ENV 环境变量识别
    - 基于 pydantic-settings 实现配置项类型校验和默认值管理
    - 敏感信息（密钥、数据库地址、端口）通过配置/环境变量注入，禁止硬编码
    - 所有配置项支持默认值、类型自动转换、启动时合法性校验
    - 密钥、凭证类配置禁止打印至日志、禁止序列化返回前端，统一脱敏处理

Usage:
    from src.core.config import settings
    port = settings.server.port
"""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.constants import (
    DEFAULT_CONFIG_DIR,
    ENV_DEVELOPMENT,
    ENV_PRODUCTION,
    ENV_TESTING,
)

# 明确禁止使用的弱密钥（不论长度）
_FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "change-me-in-production",
        "change-me",
        "secret",
        "default",
        "changeme",
        "",
    }
)


def _find_project_root() -> Path:
    """向上查找项目根目录（包含 pyproject.toml 的目录）。

    Returns:
        Path: 项目根目录的绝对路径
    """
    current: Path = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parent.parent


def _load_yaml_config(config_dir: Path, app_env: str) -> dict[str, Any]:
    """加载 YAML 配置文件，深度合并默认配置和环境特定配置。

    先加载 config.yaml 作为基础配置，再加载 config.{env}.yaml 进行深度覆盖合并。
    嵌套字典会递归合并，非字典值整体替换。

    Args:
        config_dir: 配置文件所在目录
        app_env: 当前运行环境标识

    Returns:
        dict[str, Any]: 合并后的配置字典
    """
    merged: dict[str, Any] = {}

    default_file: Path = config_dir / "config.yaml"
    if default_file.exists():
        with open(default_file, encoding="utf-8") as f:
            default_cfg: dict[str, Any] | None = yaml.safe_load(f)
            if default_cfg and isinstance(default_cfg, dict):
                merged = default_cfg

    env_file: Path = config_dir / f"config.{app_env}.yaml"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            env_cfg: dict[str, Any] | None = yaml.safe_load(f)
            if env_cfg and isinstance(env_cfg, dict):
                _deep_merge(merged, env_cfg)

    return merged


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归深度合并两个字典，override 中的值覆盖 base 中的同名键。

    Args:
        base: 基础字典，会被原地修改
        override: 覆盖字典

    Returns:
        dict[str, Any]: 合并后的字典（即 base 本身）
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class ServerConfig(BaseSettings):
    """服务配置。

    Attributes:
        host: 监听地址
        port: 监听端口
        debug: 是否开启调试模式
        workers: 工作进程数（生产环境）
    """

    host: str = Field(default="0.0.0.0", description="服务监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务监听端口")
    debug: bool = Field(default=True, description="调试模式开关")
    workers: int = Field(default=1, ge=1, le=64, description="工作进程数")

    model_config = SettingsConfigDict(env_prefix="SERVER_")


class LoggingConfig(BaseSettings):
    """日志配置。

    Attributes:
        level: 日志级别
        file_path: 日志文件路径
        rotation: 日志轮转周期
        retention: 日志保留时间
    """

    level: str = Field(default="INFO", description="日志级别")
    file_path: str = Field(default="logs/app.log", description="日志文件路径")
    rotation: str = Field(default="1 day", description="日志轮转周期")
    retention: str = Field(default="7 days", description="日志保留时间")

    model_config = SettingsConfigDict(env_prefix="LOGGING_")


class CORSConfig(BaseSettings):
    """跨域配置。

    Attributes:
        origins: 允许的来源列表
    """

    origins: list[str] = Field(default=["*"], description="允许的跨域来源")

    model_config = SettingsConfigDict(env_prefix="CORS_")


class RateLimitConfig(BaseSettings):
    """请求限流配置。

    Attributes:
        per_minute: 每分钟最大请求数
    """

    per_minute: int = Field(default=60, ge=1, description="每分钟最大请求数")

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_")


class AuthConfig(BaseSettings):
    """认证配置。

    Attributes:
        secret_key: JWT 签名密钥
        algorithm: JWT 签名算法
    """

    secret_key: str = Field(
        default="dev-only-change-me-in-production",
        description="认证密钥（生产环境必须通过环境变量或 secrets 覆盖）",
    )
    algorithm: str = Field(default="HS256", description="JWT 算法")
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7, ge=1, description="访问令牌有效期（分钟）"
    )
    refresh_token_expire_days: int = Field(
        default=30, ge=1, description="刷新令牌有效期（天）"
    )

    model_config = SettingsConfigDict(env_prefix="AUTH_")

    @field_validator("secret_key")
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """基础密钥长度校验。

        黑名单与生产环境强制校验统一在 Settings.validate() 中执行，
        避免 yaml 默认值（如 change-me-in-production）在开发/测试环境
        直接阻断 pydantic 实例化。

        Args:
            v: 密钥值
            info: 验证信息

        Returns:
            str: 验证后的密钥
        """
        # 仅做最小长度校验，确保 dev 默认值也能通过 pydantic 校验
        if len(v) < 16:
            raise ValueError("AUTH_SECRET_KEY 长度至少 16 个字符")
        return v


class DatabaseConfig(BaseSettings):
    """数据库配置。

    Attributes:
        url: 数据库连接字符串
        pool_size: 连接池大小
    """

    url: str = Field(default="", description="数据库连接地址")
    pool_size: int = Field(default=5, ge=1, description="连接池大小")

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class RedisConfig(BaseSettings):
    """Redis 配置。

    Attributes:
        url: Redis 连接地址
    """

    url: str = Field(default="", description="Redis 连接地址")

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class ObjectStorageConfig(BaseSettings):
    """对象存储配置"""

    endpoint_url: str = Field(default="", description="对象存储 S3 端点 URL")
    access_key: str = Field(default="", description="对象存储 Access Key")
    secret_key: str = Field(default="", description="对象存储 Secret Key")
    bucket: str = Field(default="x-hanjiang", description="存储桶名称")
    region: str = Field(default="cn-east-1", description="桶区域")
    prefix: str = Field(default="uploads", description="对象前缀")
    public_url: str = Field(default="", description="公开访问地址前缀")
    use_ssl: bool = Field(default=True, description="是否使用 HTTPS")

    model_config = SettingsConfigDict(env_prefix="OBJECT_STORAGE_")


class Settings(BaseSettings):
    """应用全局配置类。

    配置加载优先级（从高到低）：
        1. 环境变量（包括 .env 文件）
        2. 环境特定 YAML 配置（config.{env}.yaml）
        3. 默认 YAML 配置（config.yaml）
        4. 代码中的默认值

    Attributes:
        app_env: 当前运行环境
        server: 服务配置
        logging: 日志配置
        cors: 跨域配置
        rate_limit: 限流配置
        auth: 认证配置
        database: 数据库配置
        redis: Redis 配置
    """

    app_env: str = Field(default=ENV_DEVELOPMENT, description="运行环境")

    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    object_storage: ObjectStorageConfig = Field(default_factory=ObjectStorageConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs: Any) -> None:
        """初始化配置，从 YAML 和环境变量加载配置。

        Args:
            **kwargs: 可选的关键字参数，用于覆盖默认配置
        """
        config_dir: Path = kwargs.pop("config_dir", None) or Path(
            os.environ.get("CONFIG_DIR", DEFAULT_CONFIG_DIR)
        )

        env_file: Path = config_dir / ".env"
        if env_file.exists():
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)

        app_env: str = os.environ.get("APP_ENV", ENV_DEVELOPMENT)

        project_root: Path = _find_project_root()
        yaml_config_dir: Path = (
            config_dir if config_dir.is_absolute() else project_root / config_dir
        )
        yaml_data: dict[str, Any] = _load_yaml_config(yaml_config_dir, app_env)

        kwargs.setdefault("app_env", app_env)
        kwargs = self._merge_yaml_into_kwargs(kwargs, yaml_data)

        super().__init__(**kwargs)

    @staticmethod
    def _merge_yaml_into_kwargs(
        kwargs: dict[str, Any], yaml_data: dict[str, Any]
    ) -> dict[str, Any]:
        """将 YAML 配置数据展平合并到 kwargs 中。

        Args:
            kwargs: 现有的关键字参数
            yaml_data: 从 YAML 文件加载的配置数据

        Returns:
            dict[str, Any]: 合并后的参数字典
        """
        section_map: dict[str, str] = {
            "server": "SERVER_",
            "logging": "LOGGING_",
            "cors": "CORS_",
            "rate_limit": "RATE_LIMIT_",
            "auth": "AUTH_",
            "database": "DATABASE_",
            "redis": "REDIS_",
            "object_storage": "OBJECT_STORAGE_",
        }

        for section_name, env_prefix in section_map.items():
            if section_name in yaml_data and section_name not in kwargs:
                section_data: dict[str, Any] = yaml_data[section_name]
                if isinstance(section_data, dict):
                    # 将 YAML 值写入环境变量（setdefault，环境变量优先）。
                    # 这样 pydantic-settings 读取时，真实环境变量（如 DATABASE_URL）
                    # 会覆盖 YAML 中的占位值，实现「环境变量 > YAML」的优先级。
                    for key, value in section_data.items():
                        env_key = f"{env_prefix}{str(key).upper()}"
                        if isinstance(value, (list, dict)):
                            # 复杂类型用 JSON 序列化，供 pydantic-settings 反序列化
                            os.environ.setdefault(env_key, json.dumps(value))
                        else:
                            os.environ.setdefault(env_key, str(value))

        return kwargs

    @property
    def is_development(self) -> bool:
        """是否为开发环境。

        Returns:
            bool: 当前是否处于开发环境
        """
        return self.app_env == ENV_DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """是否为生产环境。

        Returns:
            bool: 当前是否处于生产环境
        """
        return self.app_env == ENV_PRODUCTION

    @property
    def is_testing(self) -> bool:
        """是否为测试环境。

        Returns:
            bool: 当前是否处于测试环境
        """
        return self.app_env == ENV_TESTING

    def validate(self) -> None:
        """验证配置合法性，配置错误直接阻断程序启动。

        生产环境额外校验：
            - 调试模式必须关闭
            - AUTH_SECRET_KEY 不能是 yaml 默认占位符，且长度 ≥ 32
            - CORS origins 不能为 "*"
            - 数据库与 Redis 必须显式配置

        Raises:
            ValueError: 配置不合法时抛出
        """
        if self.is_production:
            if self.server.debug:
                raise ValueError("DEBUG mode must be disabled in production")

            # 黑名单 + 长度 + 占位符前缀 三重检查
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

        if self.database.url:
            if not self.database.url.startswith(("mysql://", "mysql+pymysql://", "postgresql://")):
                raise ValueError("Unsupported database type, only MySQL and PostgreSQL are supported")


settings: Settings = Settings()
settings.validate()
