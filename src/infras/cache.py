#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存基础设施模块

本模块提供 Redis 客户端封装和连接管理，支持连接复用和序列化。

功能特性：
    - Redis 客户端初始化和配置
    - 连接池管理
    - 通用序列化/反序列化
    - 支持连接自动释放

Usage:
    from src.infras.cache import get_redis, cache

    # 获取 Redis 客户端
    redis_client = get_redis()
    redis_client.set("key", "value")

    # 使用缓存装饰器
    @cache(key="user:{user_id}", ttl=3600)
    def get_user(user_id: int) -> User:
        ...
"""

import json
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from src.core.config import settings
from src.core.logger import logger

try:
    import redis
    from redis import Redis
except ImportError:
    redis = None
    Redis = None  # type: ignore[assignment]

_redis_client: Optional[Redis] = None

T = TypeVar("T")


def get_redis() -> Redis:
    """获取 Redis 客户端单例。

    Returns:
        Redis: Redis 客户端实例

    Raises:
        ValueError: REDIS_URL 配置为空时抛出
        ImportError: redis 库未安装时抛出
    """
    global _redis_client

    if redis is None:
        raise ImportError("redis 库未安装，请运行 pip install redis")

    if _redis_client is None:
        redis_url: str = settings.redis.REDIS_URL
        if not redis_url:
            raise ValueError("REDIS_URL 配置不能为空，请在配置文件或环境变量中设置")

        _redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30,
        )

        try:
            _redis_client.ping()
            logger.info(f"Redis client initialized: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    return _redis_client


def close_redis() -> None:
    """关闭 Redis 连接，清理资源。"""
    global _redis_client

    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def cache(key: str, ttl: int = 3600) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """缓存装饰器。

    为函数结果提供 Redis 缓存支持，自动处理缓存的读取和写入。

    Usage:
        @cache(key="user:{user_id}", ttl=3600)
        def get_user(user_id: int) -> User:
            return db.query(User).get(user_id)

    Args:
        key: 缓存键模板，支持占位符（如 "user:{user_id}"）
        ttl: 缓存过期时间（秒）

    Returns:
        Callable: 包装后的函数，自动处理缓存逻辑
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                redis_client = get_redis()
            except (ValueError, ImportError):
                return func(*args, **kwargs)

            all_args: dict[str, Any] = kwargs.copy()
            all_args.update(enumerate(args))

            cache_key: str = key.format(**all_args)

            cached_value = redis_client.get(cache_key)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    pass

            result: T = func(*args, **kwargs)

            try:
                redis_client.setex(cache_key, ttl, json.dumps(result))
            except Exception as e:
                logger.warning(f"Failed to set cache: {e}")

            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str, *args: Any, **kwargs: Any) -> None:
    """根据模式清除缓存。

    Args:
        pattern: 缓存键模式，支持占位符
        *args: 位置参数
        **kwargs: 关键字参数
    """
    try:
        redis_client = get_redis()
    except (ValueError, ImportError):
        return

    all_args: dict[str, Any] = kwargs.copy()
    all_args.update(enumerate(args))

    cache_pattern: str = pattern.format(**all_args)

    try:
        for key in redis_client.keys(cache_pattern):
            redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")


__all__ = ["get_redis", "close_redis", "cache", "invalidate_cache"]