#!/usr/bin/env python3
"""健康检查业务服务。

承载健康检查的下游探测（数据库 / Redis 连通性）与故障告警编排，
API 层只负责组装响应。告警带节流（同一组件 5 分钟内不重复发送）。

依赖说明：
- 数据库 / 缓存探测经 infras 的 provider 抽象懒加载，健康检查不依赖
  数据库本身可用（DB 故障时仍能如实返回 error 状态）；
- 告警服务在触发时懒构造（session=None），避免因 DB 故障导致健康检查接口失败。
"""

import time

from src.core.config import settings
from src.core.logger import logger

# 告警节流：{ component: last_alert_timestamp }
_alert_throttle: dict[str, float] = {}
_ALERT_COOLDOWN_SECONDS = 300  # 同一组件 5 分钟内不重复告警


class HealthService:
    """健康检查服务：下游探测 + 故障告警（带节流）。"""

    def check(self) -> dict[str, str]:
        """探测数据库与缓存连通性，故障时自动触发告警。

        Returns:
            dict[str, str]: {"database": "ok|error|disabled", "cache": "ok|error|disabled"}
        """
        database_status = self.check_database()
        cache_status = self.check_cache()
        if database_status == "error":
            self._trigger_alert("database", "数据库连接异常")
        if cache_status == "error":
            self._trigger_alert("cache", "Redis 缓存连接异常")
        return {"database": database_status, "cache": cache_status}

    def check_database(self) -> str:
        """检查数据库连接状态。"""
        if not settings.database.url:
            return "disabled"
        try:
            from sqlalchemy import text

            from src.infras.database import get_cached_database_provider

            engine = get_cached_database_provider().get_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return "ok"
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Database connection check failed: {e}")
            return "error"

    def check_cache(self) -> str:
        """检查缓存连接状态。"""
        if not settings.redis.url:
            return "disabled"
        try:
            from src.infras.cache import get_cached_cache_provider

            provider = get_cached_cache_provider()
            provider.ping()
            return "ok"
        except ImportError:
            return "disabled"
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis connection check failed: {e}")
            return "error"

    def _trigger_alert(self, component: str, message: str) -> None:
        """触发告警（带节流，同一组件 5 分钟内不重复发送）。"""
        now = time.time()
        if now - _alert_throttle.get(component, 0) < _ALERT_COOLDOWN_SECONDS:
            return
        _alert_throttle[component] = now
        try:
            from src.infras.notification import get_registry
            from src.notification.dispatcher import NotificationDispatcher
            from src.services.alert_service import AlertService

            alert_email = settings.notification.alert_email
            if not alert_email:
                logger.warning("Health check alert skipped: notification.alert_email not configured")
                return
            dispatcher = NotificationDispatcher(registry=get_registry(), session=None)
            service = AlertService(dispatcher=dispatcher, session=None)
            service.send(
                subject=f"[健康检查] {component} 故障",
                message=f"健康检查检测到 {message}，请立即排查。",
                recipients={"email": alert_email},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Health check alert trigger failed: {e}")
