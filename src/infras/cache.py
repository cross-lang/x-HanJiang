#!/usr/bin/env python3
"""
缓存基础设施模块

本模块提供缓存提供者抽象和 Redis 实现，支持连接管理和序列化。

功能特性：
    - CacheProvider 抽象接口
    - RedisCacheProvider 实现
    - 工厂函数和应用级单例缓存

Usage:
    from src.infras.cache import get_cached_cache_provider

    provider = get_cached_cache_provider()
    provider.set("key", "value", ttl=3600)
    value = provider.get("key")
"""

import json
from abc import ABC, abstractmethod
from typing import Any

from src.core.config import settings
from src.core.logger import logger

try:
    import redis
    from redis import Redis
except ImportError:
    redis = None
    Redis = None  # type: ignore[assignment]


# ============================================================
# 抽象基类
# ============================================================

class CacheProvider(ABC):
    """缓存提供者抽象接口。

    所有缓存后端必须实现此接口。业务层仅依赖此抽象，
    切换缓存实现只需修改配置，无需改动任何业务代码。
    """

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存值，未命中返回 None。"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """写入缓存，设置过期时间（秒）。"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存键。"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """判断缓存键是否存在。"""

    @abstractmethod
    def clear_pattern(self, pattern: str) -> None:
        """根据模式清除缓存。"""

    @abstractmethod
    def atomic_incr(self, key: str, ttl: int | None = None) -> int:
        """原子递增，可选设置 TTL（用于计数器/限流）。"""

    @abstractmethod
    def ping(self) -> bool:
        """检测缓存连接是否可用。"""

    @abstractmethod
    def close(self) -> None:
        """关闭连接，释放资源。"""


# ============================================================
# Redis 实现
# ============================================================

class RedisCacheProvider(CacheProvider):
    """Redis 缓存实现。"""

    def __init__(self, redis_url: str) -> None:
        if redis is None:
            raise ImportError("redis 库未安装，请运行 pip install redis")
        self._client: Redis = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
        try:
            self._client.ping()
            logger.info(f"RedisCacheProvider initialized: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Any | None:
        try:
            cached = self._client.get(key)
            if cached is None:
                return None
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return cached
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            self._client.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False

    def clear_pattern(self, pattern: str) -> None:
        try:
            for key in self._client.keys(pattern):
                self._client.delete(key)
        except Exception as e:
            logger.warning(f"Cache clear_pattern failed for '{pattern}': {e}")

    def atomic_incr(self, key: str, ttl: int | None = None) -> int:
        """原子递增，可选设置 TTL。用于计数器和限流场景。"""
        try:
            value = self._client.incr(key)
            if ttl is not None and value == 1:
                self._client.expire(key, ttl)
            return value
        except Exception as e:
            logger.warning(f"Cache atomic_incr failed for key '{key}': {e}")
            return 0

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        """暴露底层 Redis 客户端（仅供需要原生 Redis 操作的场景使用）。"""
        return self._client


# ============================================================
# 工厂函数
# ============================================================

def get_cache_provider() -> CacheProvider:
    """根据配置创建缓存实例。"""
    redis_url: str = settings.redis.url
    if not redis_url:
        raise ValueError("REDIS_URL 配置不能为空，请在配置文件或环境变量中设置")
    return RedisCacheProvider(redis_url=redis_url)


# 模块级缓存实例
_cache_provider: CacheProvider | None = None


def get_cached_cache_provider() -> CacheProvider:
    """获取缓存的缓存提供者（应用级别单例）。"""
    global _cache_provider
    if _cache_provider is None:
        _cache_provider = get_cache_provider()
    return _cache_provider


__all__ = [
    "CacheProvider",
    "RedisCacheProvider",
    "get_cache_provider",
    "get_cached_cache_provider",
]
