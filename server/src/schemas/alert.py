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
