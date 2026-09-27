"""系统级通知配置服务。

仅调用 SystemNotificationConfigRepository 存取数据，不直接操作数据库会话。
"""

import shutil
import time
from typing import Any

import psutil

from src.core.logger import logger
from src.repositories.system_notification_config_repository import (
    SystemNotificationConfigRepository,
)

# 网络 IO 上次采样快照（模块级缓存，用于计算速率）
_last_net_counters: dict[str, float] = {"ts": 0.0, "bytes_sent": 0.0, "bytes_recv": 0.0}


def _disk_status(used_pct: float) -> str:
    if used_pct > 90:
        return "critical"
    if used_pct > 80:
        return "warning"
    return "ok"


def _usage_status(pct: float) -> str:
    if pct > 90:
        return "critical"
    if pct > 75:
        return "warning"
    return "ok"


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
        return {
            "cpu": self._cpu_info(),
            "memory": self._memory_info(),
            "disk": self._disk_info(),
            "network": self._network_info(),
            "uptime": self._uptime(),
        }

    # ── CPU ──────────────────────────────────────────────
    def _cpu_info(self) -> dict[str, Any]:
        percent = psutil.cpu_percent(interval=0.3)
        per_core = psutil.cpu_percent(interval=0.3, percpu=True)
        freq = psutil.cpu_freq()
        return {
            "percent": round(percent, 1),
            "core_count": psutil.cpu_count(logical=False),
            "thread_count": psutil.cpu_count(logical=True),
            "freq_mhz": round(freq.current, 0) if freq else None,
            "status": _usage_status(percent),
        }

    # ── 内存 ─────────────────────────────────────────────
    def _memory_info(self) -> dict[str, Any]:
        vm = psutil.virtual_memory()
        used = vm.total - vm.available
        return {
            "total_gb": round(vm.total / 1024**3, 1),
            "used_gb": round(used / 1024**3, 1),
            "available_gb": round(vm.available / 1024**3, 1),
            "percent": round(vm.percent, 1),
            "status": _usage_status(vm.percent),
        }

    # ── 磁盘 ─────────────────────────────────────────────
    def _disk_info(self) -> dict[str, Any]:
        disk = shutil.disk_usage("/")
        used_pct = round(disk.used / disk.total * 100, 1)
        return {
            "total_gb": round(disk.total / 1024**3, 1),
            "used_gb": round(disk.used / 1024**3, 1),
            "free_gb": round(disk.free / 1024**3, 1),
            "used_percent": used_pct,
            "status": _disk_status(used_pct),
        }

    # ── 网络 IO（速率，基于两次采样）──────────────────────
    def _network_info(self) -> dict[str, Any]:
        global _last_net_counters
        counters = psutil.net_io_counters()
        now = time.time()
        prev_ts = _last_net_counters["ts"]
        interval = now - prev_ts if prev_ts else 0.0

        if interval > 0.1:
            sent_rate = (counters.bytes_sent - _last_net_counters["bytes_sent"]) / interval
            recv_rate = (counters.bytes_recv - _last_net_counters["bytes_recv"]) / interval
            _last_net_counters = {
                "ts": now,
                "bytes_sent": float(counters.bytes_sent),
                "bytes_recv": float(counters.bytes_recv),
            }
        else:
            sent_rate = 0.0
            recv_rate = 0.0
            if prev_ts == 0.0:
                _last_net_counters = {
                    "ts": now,
                    "bytes_sent": float(counters.bytes_sent),
                    "bytes_recv": float(counters.bytes_recv),
                }

        return {
            "bytes_sent_total_mb": round(counters.bytes_sent / 1024**2, 1),
            "bytes_recv_total_mb": round(counters.bytes_recv / 1024**2, 1),
            "send_kbps": round(sent_rate / 1024, 1),
            "recv_kbps": round(recv_rate / 1024, 1),
        }

    # ── 运行时间 ─────────────────────────────────────────
    def _uptime(self) -> dict[str, Any]:
        boot = psutil.boot_time()
        uptime_sec = time.time() - boot
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        return {
            "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot)),
            "uptime_text": f"{days}天{hours}小时",
        }
