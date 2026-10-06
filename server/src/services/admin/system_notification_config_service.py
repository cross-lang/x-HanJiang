#!/usr/bin/env python3
"""系统通知渠道配置业务逻辑。

系统级通知渠道配置（system_notification_configs）：
查询全部渠道配置、按渠道 upsert（update_config 后由路由层重建 Provider，无需重启）。
数据访问仅经 SystemNotificationConfigRepository。
"""

from __future__ import annotations

from src.core.logger import logger
from src.models.entities.system_notification_config_entity import SystemNotificationConfigEntity
from src.repositories.system_notification_config_repository import SystemNotificationConfigRepository


class SystemNotificationConfigService:
    """系统通知渠道配置业务逻辑实现。"""

    def __init__(self, repository: SystemNotificationConfigRepository) -> None:
        """初始化配置服务。

        Args:
            repository: 系统通知配置数据访问仓库
        """
        self._repository = repository

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
