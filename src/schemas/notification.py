"""通知相关数据模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.constants.enums import NotificationChannel, NotificationEvent


class NotificationSendRequest(BaseModel):
    """通知发送请求。

    默认根据当前登录用户的通知渠道配置自动发送。
    也可通过 recipients 手动指定接收人（调试用）。

    示例（自动发送，从用户配置获取渠道）::

        {
            "event_type": "user.registered",
            "variables": { "username": "张三" }
        }

    示例（手动指定接收人，调试用）::

        {
            "event_type": "user.password_changed",
            "recipients": {
                "email": "zhangsan@example.com",
                "dingtalk": "zhangsan"
            },
            "variables": { "username": "张三", "changed_at": "2026-09-23 10:00" },
            "channels": ["email", "dingtalk"],
            "metadata": { "source": "admin_panel" }
        }
    """

    event_type: NotificationEvent = Field(
        description="事件类型，决定使用哪套模板",
        examples=[
            NotificationEvent.USER_REGISTERED,
            NotificationEvent.USER_PASSWORD_CHANGED,
            NotificationEvent.SYSTEM_ALERT,
        ],
    )
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="模板变量，注入到模板的 `{变量名}` 占位符中",
        examples=[{"username": "张三"}, {"order_no": "ORD001", "amount": "99.00"}],
    )
    channels: list[str] | None = Field(
        default=None,
        description="指定实际发送的渠道（覆盖事件默认路由表），省略则使用默认路由",
        examples=[["email", "dingtalk"]],
    )
    recipients: dict[str, str] | None = Field(
        default=None,
        description="手动指定渠道→接收人映射（调试用），省略则从当前用户配置自动获取",
        examples=[{"email": "zhangsan@example.com", "dingtalk": "zhangsan"}],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="扩展元数据，写入通知记录，可用于追溯来源",
        examples=[{"source": "admin_panel", "operator_id": 42}],
    )


class NotificationRecordResponse(BaseModel):
    """通知记录响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="记录ID")
    event_type: str = Field(description="事件类型")
    channel: str = Field(description="发送渠道")
    recipient: str = Field(description="接收人")
    subject: str = Field(description="通知主题")
    content: str = Field(description="渲染后正文")
    status: str = Field(description="发送状态")
    retry_count: int = Field(description="已重试次数")
    error_message: str | None = Field(default=None, description="错误信息")
    created_at: datetime = Field(description="创建时间")
    sent_at: datetime | None = Field(default=None, description="发送时间")


class NotificationStatsResponse(BaseModel):
    """通知统计响应。"""

    total: int = Field(description="总通知数")
    success: int = Field(description="成功数")
    failed: int = Field(description="失败数")
    pending: int = Field(description="待发送数")


# ── 用户通知渠道配置 ──────────────────────────────────────


class UserNotificationConfigResponse(BaseModel):
    """用户通知渠道配置响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="配置ID")
    user_id: int = Field(description="用户ID")
    channel: str = Field(description="通知渠道（email/sms/dingtalk/feishu）")
    recipient: str = Field(description="渠道接收人标识")
    enabled: bool = Field(description="是否启用")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class UserNotificationConfigCreateRequest(BaseModel):
    """创建/更新用户通知渠道配置请求。

    如果该用户+渠道已存在则更新，不存在则创建（upsert 语义）。
    """

    channel: NotificationChannel = Field(
        description="通知渠道",
    )
    recipient: str = Field(
        min_length=1, max_length=256, description="渠道接收人标识"
    )
    enabled: bool = Field(default=True, description="是否启用")


class UserNotificationConfigUpdateRequest(BaseModel):
    """更新用户通知渠道配置请求（部分更新）。"""

    recipient: str | None = Field(
        default=None, min_length=1, max_length=256, description="渠道接收人标识"
    )
    enabled: bool | None = Field(default=None, description="是否启用")
