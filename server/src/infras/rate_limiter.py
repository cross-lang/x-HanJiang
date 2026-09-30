#!/usr/bin/env python3
"""请求限流基础设施模块。

提供 RateLimiterProvider 抽象接口，应用装配层（main.py）仅依赖此抽象，
切换限流实现（slowapi → 自研 Redis 令牌桶 / 网关限流等）无需改动装配代码。
当前实现基于 slowapi（每 IP 每分钟请求数），slowapi 不可用时降级为空实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fastapi import FastAPI

from src.core.config import settings
from src.core.logger import logger


# ============================================================
# 抽象基类
# ============================================================
class RateLimiterProvider(ABC):
    """请求限流器抽象接口。

    所有限流后端必须实现 setup()：负责把限流器装配到 FastAPI 应用
    （挂载 app.state、注册 429 异常处理等），业务层不感知具体实现。
    """

    @abstractmethod
    def setup(self, app: FastAPI) -> None:
        """在应用上装配限流器。"""


# ============================================================
# 空实现（限流关闭 / slowapi 不可用）
# ============================================================
class DisabledRateLimiterProvider(RateLimiterProvider):
    """限流关闭或不可用时的空实现（无操作）。"""

    def setup(self, app: FastAPI) -> None:
        logger.info("Rate limiter disabled (slowapi not installed or settings.rate_limit.enabled=false)")


# ============================================================
# slowapi 实现
# ============================================================
class SlowApiRateLimiterProvider(RateLimiterProvider):
    """基于 slowapi 的限流实现（按客户端 IP 限流）。

    从 Settings 读取每 IP 每分钟允许的请求数，挂载到应用 state，
    并注册 RateLimitExceeded 异常处理（返回 429）。
    """

    def setup(self, app: FastAPI) -> None:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        limiter: Limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{settings.rate_limit.per_minute}/minute"],
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
        logger.info(f"Rate limiter enabled: {settings.rate_limit.per_minute} req/min per IP")


# ============================================================
# 工厂函数
# ============================================================
def get_rate_limiter_provider() -> RateLimiterProvider:
    """根据配置创建限流器实现；slowapi 不可用或配置关闭时降级为空实现。"""
    if not settings.rate_limit.enabled:
        return DisabledRateLimiterProvider()
    try:
        from slowapi import Limiter  # noqa: F401

        return SlowApiRateLimiterProvider()
    except ImportError:
        logger.warning("slowapi not installed, rate limiter disabled")
        return DisabledRateLimiterProvider()


# 模块级缓存实例
_rate_limiter_provider: RateLimiterProvider | None = None


def get_cached_rate_limiter_provider() -> RateLimiterProvider:
    """获取缓存的限流器（应用级别单例）。"""
    global _rate_limiter_provider
    if _rate_limiter_provider is None:
        _rate_limiter_provider = get_rate_limiter_provider()
    return _rate_limiter_provider


__all__ = [
    "RateLimiterProvider",
    "DisabledRateLimiterProvider",
    "SlowApiRateLimiterProvider",
    "get_rate_limiter_provider",
    "get_cached_rate_limiter_provider",
]
