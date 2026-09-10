#!/usr/bin/env python3
"""
登录会话存储（有状态 JWT / 混合会话）

对标 Go 服务的 Redis 登录态维护：
    SetLoginStatus   -> 登录时写入 login:{user_id} = token（TTL = 刷新令牌有效期）
    GetLoginStatus   -> 鉴权时校验该用户是否处于登录态
    ClearLoginStatus -> 登出时删除 login:{user_id}

JWT 仍作为令牌载体，真正的"是否登录"判据来自 Redis，从而实现即时登出。
"""

from typing import Any

from src.core.config import settings
from src.core.logger import logger

try:
    from src.infras.cache import get_redis

    _HAS_REDIS = True
except ImportError:  # pragma: no cover
    _HAS_REDIS = False


def _key(user_id: int) -> str:
    """登录态键名。"""
    return f"login:{user_id}"


def set_login_status(user_id: int, token: str, ttl_seconds: int) -> None:
    """写入用户登录态（覆盖式，天然支持单设备登录）。

    存储当前有效的访问令牌；新登录/刷新会覆盖该值，
    使旧令牌在下次校验时因不匹配而失效。对标 Go 的 SetLoginStatus。

    Args:
        user_id: 用户ID
        token: 当前有效的访问令牌
        ttl_seconds: 过期秒数（建议等于刷新令牌有效期）
    """
    if not _HAS_REDIS or not settings.redis.url:
        return
    try:
        redis_client = get_redis()
        redis_client.set(_key(user_id), token, ex=ttl_seconds)
    except Exception as e:  # noqa: BLE001
        # 登录态写入失败不应阻断登录，仅告警
        logger.warning(f"SetLoginStatus failed for user {user_id}: {e}")


def get_login_status(user_id: int) -> str | None:
    """读取用户当前有效的登录令牌。未配置 Redis 时返回 None（放行）。

    Args:
        user_id: 用户ID

    Returns:
        str | None: 登录态令牌，未登录或异常时为 None
    """
    if not _HAS_REDIS or not settings.redis.url:
        return None
    try:
        return get_redis().get(_key(user_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"GetLoginStatus failed for user {user_id}: {e}")
        return None


def is_logged_in(user_id: int) -> bool:
    """判断用户是否处于登录态（key 存在即为登录）。

    对标 Go 的 GetLoginStatus：登出删除 key 后返回 False，令牌立即失效。
    Redis 未配置或不可用时降级放行（返回 True），不阻断登录态校验。

    Args:
        user_id: 用户ID

    Returns:
        bool: 存在登录态记录即为已登录；Redis 不可用时降级放行
    """
    if not _HAS_REDIS or not settings.redis.url:
        return True
    return get_login_status(user_id) is not None


def clear_login_status(user_id: int) -> None:
    """删除用户登录态（登出）。对标 Go 的 ClearLoginStatus。

    Args:
        user_id: 用户ID
    """
    if not _HAS_REDIS or not settings.redis.url:
        return
    try:
        get_redis().delete(_key(user_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ClearLoginStatus failed for user {user_id}: {e}")


__all__ = [
    "set_login_status",
    "get_login_status",
    "is_logged_in",
    "clear_login_status",
]
