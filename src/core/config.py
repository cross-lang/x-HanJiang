#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置管理模块

本模块实现统一配置加载逻辑，支持多环境切换，为全局唯一配置入口。
配置优先级：环境变量 > 环境特定 YAML 配置 > 默认 YAML 配置 > 代码默认值。

功能特性：
    - 支持 .env 环境变量 + config.yaml 配置文件双来源
    - 支持多环境切换（development / testing / production），通过 APP_ENV 环境变量识别
    - 基于 pydantic-settings 实现配置项类型校验和默认值管理
    - 敏感信息（密钥、数据库地址、端口）通过配置/环境变量注入，禁止硬编码

Usage:
    from src.core.config import settings
    port = settings.SERVER_PORT
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.common.constants import (
    DEFAULT_CONFIG_DIR,
    ENV_DEVELOPMENT,
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
    """加载 YAML 配置文件，合并默认配置和环境特定配置。

    先加载 config.yaml 作为基础配置，再加载 config.{env}.yaml 进行覆盖合并。

    Args:
        config_dir: 配置文件所在目录
        app_env: 当前运行环境标识

    Returns:
        dict[str, Any]: 合并后的配置字典
    """
    merged: dict[str, Any] = {}

    # 加载默认配置
    default_file: Path = config_dir / "config.yaml"
    if default_file.exists():
        with open(default_file, "r", encoding="utf-8") as f:
            default_cfg: Optional[dict[str, Any]] = yaml.safe_load(f)
            if default_cfg and isinstance(default_cfg, dict):
                merged.update(default_cfg)

    # 加载环境特定配置
    env_file: Path = config_dir / f"config.{app_env}.yaml"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            env_cfg: Optional[dict[str, Any]] = yaml.safe_load(f)
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
        SERVER_HOST: 监听地址
        SERVER_PORT: 监听端口
        SERVER_DEBUG: 是否开启调试模式
        SERVER_WORKERS: 工作进程数（生产环境）
    """

    SERVER_HOST: str = Field(default="0.0.0.0", description="服务监听地址")
    SERVER_PORT: int = Field(default=8000, ge=1, le=65535, description="服务监听端口")
    SERVER_DEBUG: bool = Field(default=True, description="调试模式开关")
    SERVER_WORKERS: int = Field(default=1, ge=1, le=64, description="工作进程数")

    model_config = SettingsConfigDict(env_prefix="SERVER_")


class LoggingConfig(BaseSettings):
    """日志配置。

    Attributes:
        LOGGING_LEVEL: 日志级别
        LOGGING_FILE_PATH: 日志文件路径
        LOGGING_ROTATION: 日志轮转周期
        LOGGING_RETENTION: 日志保留时间
    """

    LOGGING_LEVEL: str = Field(default="INFO", description="日志级别")
    LOGGING_FILE_PATH: str = Field(default="logs/app.log", description="日志文件路径")
    LOGGING_ROTATION: str = Field(default="1 day", description="日志轮转周期")
    LOGGING_RETENTION: str = Field(default="7 days", description="日志保留时间")

    model_config = SettingsConfigDict(env_prefix="LOGGING_")


class CORSConfig(BaseSettings):
    """跨域配置。

    Attributes:
        CORS_ORIGINS: 允许的来源列表
    """

    CORS_ORIGINS: list[str] = Field(default=["*"], description="允许的跨域来源")

    model_config = SettingsConfigDict(env_prefix="CORS_")


class RateLimitConfig(BaseSettings):
    """请求限流配置。

    Attributes:
        RATE_LIMIT_PER_MINUTE: 每分钟最大请求数
    """

    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1, description="每分钟最大请求数")

    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_")


class AuthConfig(BaseSettings):
    """认证配置。

    Attributes:
        AUTH_SECRET_KEY: JWT 签名密钥
        AUTH_ALGORITHM: JWT 签名算法
    """

    AUTH_SECRET_KEY: str = Field(default="change-me-in-production", description="认证密钥")
    AUTH_ALGORITHM: str = Field(default="HS256", description="JWT 算法")

    model_config = SettingsConfigDict(env_prefix="AUTH_")


class DatabaseConfig(BaseSettings):
    """数据库配置。

    Attributes:
        DATABASE_URL: 数据库连接字符串
        DATABASE_POOL_SIZE: 连接池大小
    """

    DATABASE_URL: str = Field(default="", description="数据库连接地址")
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, description="连接池大小")

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class RedisConfig(BaseSettings):
    """Redis 配置。

    Attributes:
        REDIS_URL: Redis 连接地址
    """

    REDIS_URL: str = Field(default="", description="Redis 连接地址")

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class Settings(BaseSettings):
    """应用全局配置类。

    配置加载优先级（从高到低）：
        1. 环境变量（包括 .env 文件）
        2. 环境特定 YAML 配置（config.{env}.yaml）
        3. 默认 YAML 配置（config.yaml）
        4. 代码中的默认值

    Attributes:
        APP_ENV: 当前运行环境
        server: 服务配置
        logging: 日志配置
        cors: 跨域配置
        rate_limit: 限流配置
        auth: 认证配置
        database: 数据库配置
        redis: Redis 配置
    """

    APP_ENV: str = Field(default=ENV_DEVELOPMENT, description="运行环境")

    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)

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

        # 尝试加载 .env 文件
        env_file: Path = config_dir / ".env"
        if env_file.exists():
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)

        # 获取当前环境
        app_env: str = os.environ.get("APP_ENV", ENV_DEVELOPMENT)

        # 加载 YAML 配置
        project_root: Path = _find_project_root()
        yaml_config_dir: Path = (
            config_dir if config_dir.is_absolute() else project_root / config_dir
        )
        yaml_data: dict[str, Any] = _load_yaml_config(yaml_config_dir, app_env)

        # 将 YAML 数据展平并传入父类
        kwargs.setdefault("APP_ENV", app_env)
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
        section_map: dict[str, type] = {
            "server": ServerConfig,
            "logging": LoggingConfig,
            "cors": CORSConfig,
            "rate_limit": RateLimitConfig,
            "auth": AuthConfig,
            "database": DatabaseConfig,
            "redis": RedisConfig,
        }

        for section_name, config_cls in section_map.items():
            if section_name in yaml_data and section_name not in kwargs:
                section_data: dict[str, Any] = yaml_data[section_name]
                if isinstance(section_data, dict):
                    # 展平嵌套键名，如 {origins: ["*"]} -> CORS_ORIGINS: ["*"]
                    flattened: dict[str, Any] = {}
                    env_prefix: str = config_cls.model_config.get("env_prefix", "")
                    for key, value in section_data.items():
                        upper_key: str = f"{env_prefix}{key.upper()}"
                        flattened[upper_key] = value
                    kwargs[section_name] = config_cls(**flattened)

        return kwargs

    @property
    def is_development(self) -> bool:
        """是否为开发环境。

        Returns:
            bool: 当前是否处于开发环境
        """
        return self.APP_ENV == ENV_DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """是否为生产环境。

        Returns:
            bool: 当前是否处于生产环境
        """
        from src.common.constants import ENV_PRODUCTION

        return self.APP_ENV == ENV_PRODUCTION

    @property
    def is_testing(self) -> bool:
        """是否为测试环境。

        Returns:
            bool: 当前是否处于测试环境
        """
        from src.common.constants import ENV_TESTING

        return self.APP_ENV == ENV_TESTING


# 创建全局配置单例
settings: Settings = Settings()
