"""系统级通知配置服务。

仅调用 SystemNotificationConfigRepository 存取数据，不直接操作数据库会话。
"""

import shutil
from typing import Any

from src.core.logger import logger
from src.repositories.system_notification_config_repository import (
    SystemNotificationConfigRepository,
)


class SystemNotificationService:
    """系统通知配置 & 运维监控。"""

    def __init__(self, repository: SystemNotificationConfigRepository) -> None:
        self._repository = repository

    def list_configs(self) -> list[dict[str, Any]]:
        rows = self._repository.list_all()
        return [{
            "channel": r.channel,
            "config_json": r.config_json,
            "enabled": r.enabled,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        } for r in rows]

    def update_config(self, channel: str, config_json: str, enabled: bool) -> None:
        self._repository.upsert(channel=channel, config_json=config_json, enabled=enabled)
        self._repository.commit()

    def get_system_monitor(self) -> dict[str, Any]:
        disk = shutil.disk_usage("/")
        used_pct = round(disk.used / disk.total * 100, 1)
        return {
            "disk": {
                "total_gb": round(disk.total / 1024**3, 1),
                "used_gb": round(disk.used / 1024**3, 1),
                "free_gb": round(disk.free / 1024**3, 1),
                "used_percent": used_pct,
                "status": "critical" if used_pct > 90 else "warning" if used_pct > 80 else "ok",
            }
        }
