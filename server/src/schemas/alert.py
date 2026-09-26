"""告警与维护通知相关数据模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AlertSendRequest(BaseModel):
    """系统告警发送请求。

    供外部监控系统（Prometheus Alertmanager、Sentry 等）通过 Webhook 调用。
    必须提供 recipients 指定接收人。

    示例::

        {
            "subject": "CPU 使用率超过 90%",
            "message": "服务器 node-1 CPU 使用率达到 95%，请及时处理。",
            "recipients": { "email": "admin@example.com", "dingtalk": "admin" }
        }
    """

    subject: str = Field(
        min_length=1,
        max_length=200,
        description="告警标题",
        examples=["CPU 使用率超过 90%"],
    )
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="告警内容",
        examples=["服务器 node-1 CPU 使用率达到 95%，请及时处理。"],
    )
    recipients: dict[str, str] = Field(
        description="渠道→接收人映射",
        examples=[{"email": "admin@example.com", "dingtalk": "admin"}],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="扩展元数据（如来源系统、告警级别等）",
        examples=[{"source": "prometheus", "severity": "critical"}],
    )


class MaintenanceNotifyRequest(BaseModel):
    """系统维护通知请求。

    管理员手动触发，通知全体用户即将进行的系统维护。

    示例::

        {
            "maintenance_time": "2026-09-25 02:00",
            "duration": "约 2 小时",
            "reason": "数据库升级"
        }
    """

    maintenance_time: str = Field(
        min_length=1,
        max_length=50,
        description="维护开始时间",
        examples=["2026-09-25 02:00"],
    )
    duration: str = Field(
        min_length=1,
        max_length=50,
        description="预计持续时长",
        examples=["约 2 小时"],
    )
    reason: str | None = Field(
        default=None,
        max_length=500,
        description="维护原因",
        examples=["数据库升级"],
    )
