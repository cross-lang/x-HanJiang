#!/usr/bin/env python3
"""系统通知渠道配置与系统监控业务逻辑。

提供两类能力：
1. 系统级通知渠道配置（system_notification_configs）：查询全部渠道配置、
   按渠道 upsert（update_config 后由路由层重建 Provider，无需重启）；
2. 系统运行监控（psutil）：采集 CPU / 内存 / 磁盘 / 网络 / 运行时长，
   供仪表盘监控面板展示。

数据访问仅经 SystemNotificationConfigRepository。
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import psutil

from src.core.logger import logger
from src.models.entities.system_notification_config_entity import SystemNotificationConfigEntity
from src.repositories.system_notification_config_repository import SystemNotificationConfigRepository

# 状态分级阈值：达到 75% 告警、90% 严重
_WARN_PERCENT: float = 75.0
_CRITICAL_PERCENT: float = 90.0


class SystemNotificationConfigService:
    """系统通知渠道配置与系统监控业务逻辑实现。"""

    def __init__(self, repository: SystemNotificationConfigRepository) -> None:
        """初始化配置服务。

        Args:
            repository: 系统通知配置数据访问仓库
        """
        self._repository = repository

    # ── 渠道配置 ─────────────────────────────────────────

    def list_configs(self) -> list[SystemNotificationConfigEntity]:
        """查询全部系统通知渠道配置（按渠道名升序）。

        Returns:
            list[SystemNotificationConfigEntity]: 渠道配置实体列表
        """
        return self._repository.list_all()

    def update_config(self, channel: str, config: dict, enabled: bool) -> None:
        """按渠道更新或创建配置（upsert）并提交事务。

        Args:
            channel: 通知渠道标识（email / dingtalk / feishu / station 等）
            config: 渠道配置对象（webhook 地址、密钥等）
            enabled: 是否启用该渠道
        """
        self._repository.upsert(channel=channel, config=config, enabled=enabled)
        self._repository.commit()
        logger.info("System notification config updated: channel=%s enabled=%s", channel, enabled)

    # ── 系统监控 ─────────────────────────────────────────

    def get_system_monitor(self) -> dict[str, Any]:
        """采集系统运行监控数据（CPU / 内存 / 磁盘 / 网络 / 运行时长）。

        Returns:
            dict: 监控数据，结构如下：
                uptime: {uptime_text} 运行时长文本
                cpu: {percent, core_count, thread_count, status}
                memory: {percent, used_gb, total_gb, status}
                disk: {used_percent, used_gb, total_gb, status}
                network: {recv_kbps, send_kbps, bytes_recv_total_mb, bytes_sent_total_mb}
        """
        return {
            "uptime": {"uptime_text": self._get_uptime_text()},
            "cpu": self._get_cpu_info(),
            "memory": self._get_memory_info(),
            "disk": self._get_disk_info(),
            "network": self._get_network_info(),
        }

    @staticmethod
    def _get_uptime_text() -> str:
        """计算系统运行时长文本（如：3天5小时12分钟）。"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes = remainder // 60
        return f"{days}天{hours}小时{minutes}分钟"

    @staticmethod
    def _get_cpu_info() -> dict[str, Any]:
        """采集 CPU 使用率、物理核数、逻辑线程数与状态分级。"""
        percent = psutil.cpu_percent(interval=0.1)
        return {
            "percent": round(percent, 1),
            "core_count": psutil.cpu_count(logical=False) or 1,
            "thread_count": psutil.cpu_count(logical=True) or 1,
            "status": SystemNotificationConfigService._level(percent),
        }

    @staticmethod
    def _get_memory_info() -> dict[str, Any]:
        """采集内存使用率、已用/总量（GB）与状态分级。"""
        memory = psutil.virtual_memory()
        return {
            "percent": round(memory.percent, 1),
            "used_gb": round(memory.used / (1024**3), 1),
            "total_gb": round(memory.total / (1024**3), 1),
            "status": SystemNotificationConfigService._level(memory.percent),
        }

    @staticmethod
    def _get_disk_info() -> dict[str, Any]:
        """采集根磁盘使用率、已用/总量（GB）与状态分级。"""
        disk = psutil.disk_usage("/")
        return {
            "used_percent": round(disk.percent, 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "total_gb": round(disk.total / (1024**3), 1),
            "status": SystemNotificationConfigService._level(disk.percent),
        }

    @staticmethod
    def _get_network_info() -> dict[str, Any]:
        """采集网络收发速率（KB/s）与累计流量（MB）。

        通过 0.2s 两次采样计算瞬时速率，保证低轮询频率下数值有效。
        """
        first = psutil.net_io_counters()
        time.sleep(0.2)
        second = psutil.net_io_counters()
        recv_kbps = (second.bytes_recv - first.bytes_recv) / 1024 / 0.2
        send_kbps = (second.bytes_sent - first.bytes_sent) / 1024 / 0.2
        return {
            "recv_kbps": round(max(recv_kbps, 0), 1),
            "send_kbps": round(max(send_kbps, 0), 1),
            "bytes_recv_total_mb": round(second.bytes_recv / (1024**2), 1),
            "bytes_sent_total_mb": round(second.bytes_sent / (1024**2), 1),
        }

    @staticmethod
    def _level(percent: float) -> str:
        """按使用率分级：>=90% 严重、>=75% 告警、其余正常。"""
        if percent >= _CRITICAL_PERCENT:
            return "critical"
        if percent >= _WARN_PERCENT:
            return "warning"
        return "normal"
