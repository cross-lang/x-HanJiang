"""通知相关数据模型。"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.constants.enums import NotificationChannel, SystemNotificationType

"""系统通知（广播）发布请求。
发布面向全体用户的系统通知；notice_type=maintenance 时维护字段必填。
"""


class PublishNotificationRequest(BaseModel):
    """系统通知发布请求模型。

    Attributes:
        title: 通知标题（1-200 字）
        content: 通知正文（maintenance 类型可省略，系统自动生成）
        notice_type: 通知类型（notice 普通通知 / maintenance 系统维护）
        maintenance_time: 维护开始时间（maintenance 类型必填）
        duration: 预计持续时长（maintenance 类型必填）
        reason: 维护原因（可选）
    """

    title: str = Field(min_length=1, max_length=200, description="通知标题")
    content: str | None = Field(
        default=None, max_length=5000, description="通知正文（maintenance 类型可省略，正文由系统按维护参数自动生成）"
    )
    notice_type: SystemNotificationType = Field(default=SystemNotificationType.NOTICE, description="通知类型")
    maintenance_time: str | None = Field(default=None, max_length=50, description="维护开始时间")
    duration: str | None = Field(default=None, max_length=50, description="预计持续时长")
    reason: str | None = Field(default=None, max_length=500, description="维护原因")

    @model_validator(mode="after")
    def _validate_maintenance_fields(self) -> PublishNotificationRequest:
        """普通通知必须填写正文；维护类型必须携带维护时间与时长，且时长需包含单位。"""
        if self.notice_type == SystemNotificationType.MAINTENANCE:
            if not self.maintenance_time or not self.duration:
                raise ValueError("维护类型通知必须填写维护开始时间与预计持续时长")
            if not re.search(r"(小时|时|h|分钟|分|天)", self.duration):
                raise ValueError("预计持续时长需包含单位，例如：2 小时")
            try:
                maintenance_dt = datetime.fromisoformat(self.maintenance_time)
            except ValueError:
                raise ValueError("维护时间格式不正确，应为 YYYY-MM-DD HH:mm:ss") from None
            if maintenance_dt < datetime.now():
                raise ValueError("维护时间不能早于当前时间")
        elif not self.content or not self.content.strip():
            raise ValueError("普通通知必须填写正文")
        return self


class SystemNotificationResponse(BaseModel):
    """系统通知响应模型（发布/撤回/列表/详情）。"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="系统通知 ID")
    title: str = Field(description="通知标题")
    content: str = Field(description="通知正文")
    notice_type: str = Field(description="通知类型（notice/maintenance）")
    maintenance_time: str | None = Field(default=None, description="维护开始时间")
    duration: str | None = Field(default=None, description="预计持续时长")
    reason: str | None = Field(default=None, description="维护原因")
    status: str = Field(description="发布状态（published/withdrawn）")
    operator_id: int | None = Field(default=None, description="操作人用户 ID")
    operator_name: str | None = Field(default=None, description="操作人用户名")
    published_at: datetime | None = Field(default=None, description="发布时间")
    withdrawn_at: datetime | None = Field(default=None, description="撤回时间")
    created_at: datetime | None = Field(default=None, description="创建时间")


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
    recipient: str = Field(min_length=1, max_length=256, description="渠道接收人标识")
    enabled: bool = Field(default=True, description="是否启用")


class UserNotificationConfigUpdateRequest(BaseModel):
    """更新用户通知渠道配置请求（部分更新）。"""

    recipient: str | None = Field(default=None, min_length=1, max_length=256, description="渠道接收人标识")
    enabled: bool | None = Field(default=None, description="是否启用")


class UpdateNotificationConfigRequest(BaseModel):
    """更新系统通知渠道配置请求。
    对应 system_notification_configs 表的 config_json 与 enabled 字段。
    """

    config_json: str = Field(default="{}", description="渠道配置 JSON 字符串")
    enabled: bool = Field(default=True, description="是否启用该渠道")
