"""通知相关数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.constants.enums import NotificationChannel, NotificationTargetType, SystemNotificationType


class PublishNotificationRequest(BaseModel):
    """系统通知发布请求模型。

    类型（notice/maintenance）仅表达语义标签；正文拼接与多渠道强推
    与类型解耦，由参数驱动：
    - 携带维护参数（maintenance_time/duration_hours）时，正文可省略，由系统自动拼接；
    - 指定 push_channels 时，在站内信广播基础上额外按用户配置的多渠道强推；
    - 指定 target_type/target_roles/target_user_ids 时，可定向发布而非全员广播；
    - 指定 client_request_id 时，同一幂等键重复提交返回首次发布结果（不重复广播）。

    Attributes:
        title: 通知标题（1-200 字）
        content: 通知正文（携带维护参数时可省略，系统自动生成）
        notice_type: 通知类型（notice 普通通知 / maintenance 系统维护）
        maintenance_time: 维护开始时间（可选，与 duration_hours 成对出现，须晚于当前时间）
        duration_hours: 预计持续时长（小时数，可选，整数或小数）
        reason: 维护原因（可选）
        push_channels: 强推渠道列表（可选，站内信已默认广播，仅支持 email/dingtalk/feishu）
        client_request_id: 发布幂等键（可选，8-64 位，重复提交返回首次结果）
        target_type: 发布受众类型（all 全员 / roles 指定角色 / users 指定用户）
        target_roles: 目标角色编码列表（target_type=roles 时必填）
        target_user_ids: 目标用户 ID 列表（target_type=users 时必填）
    """

    title: str = Field(min_length=1, max_length=200, description="通知标题")
    content: str | None = Field(
        default=None, max_length=5000, description="通知正文（携带维护参数时可省略，正文由系统按维护参数自动生成）"
    )
    notice_type: SystemNotificationType = Field(default=SystemNotificationType.NOTICE, description="通知类型")
    maintenance_time: str | None = Field(default=None, max_length=50, description="维护开始时间")
    duration_hours: float | None = Field(
        default=None, gt=0, le=720, description="预计持续时长（小时数，整数或小数）"
    )
    reason: str | None = Field(default=None, max_length=500, description="维护原因")
    push_channels: list[NotificationChannel] | None = Field(
        default=None, description="强推渠道列表（站内信已默认广播，仅支持 email/dingtalk/feishu）"
    )
    client_request_id: str | None = Field(
        default=None, min_length=8, max_length=64, description="发布幂等键（重复提交返回首次结果）"
    )
    target_type: NotificationTargetType = Field(
        default=NotificationTargetType.ALL, description="发布受众类型（all/roles/users）"
    )
    target_roles: list[str] | None = Field(
        default=None, max_length=20, description="目标角色编码列表（target_type=roles 时必填）"
    )
    target_user_ids: list[int] | None = Field(
        default=None, max_length=1000, description="目标用户 ID 列表（target_type=users 时必填）"
    )

    @model_validator(mode="after")
    def _validate_publish_params(self) -> PublishNotificationRequest:
        """参数驱动校验：维护参数成对出现、正文兜底、强推渠道合法、受众参数合法。"""
        has_maintenance_params = bool(self.maintenance_time or self.duration_hours)
        if has_maintenance_params:
            if not self.maintenance_time or not self.duration_hours:
                raise ValueError("携带维护参数时必须同时提供维护开始时间与预计持续时长（小时数）")
            try:
                maintenance_dt = datetime.fromisoformat(self.maintenance_time)
            except ValueError:
                raise ValueError("维护时间格式不正确，应为 YYYY-MM-DD HH:mm:ss") from None
            if maintenance_dt < datetime.now():
                raise ValueError("维护时间不能早于当前时间")
        if not has_maintenance_params and (not self.content or not self.content.strip()):
            raise ValueError("普通通知必须填写正文")
        if self.push_channels:
            for channel in self.push_channels:
                if channel == NotificationChannel.STATION:
                    raise ValueError("站内信已默认广播全体用户，无需选择强推渠道")
                if channel == NotificationChannel.SMS:
                    raise ValueError("短信渠道尚未接入，暂不支持强推")
        if self.target_type == NotificationTargetType.ROLES and not self.target_roles:
            raise ValueError("按角色定向发布时必须提供 target_roles 角色编码列表")
        if self.target_type == NotificationTargetType.USERS and not self.target_user_ids:
            raise ValueError("按用户定向发布时必须提供 target_user_ids 用户 ID 列表")
        return self


class SystemNotificationResponse(BaseModel):
    """系统通知响应模型（发布/撤回/列表/详情）。

    维护参数（maintenance_time/duration_hours/reason）不再独立暴露，
    统一从 metadata_json 读取；事件类型固定 system.notice，不再出参。
    """

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="系统通知 ID")
    title: str = Field(description="通知标题")
    content: str = Field(description="通知正文")
    notice_type: str = Field(description="通知类型（notice/maintenance）")
    status: str = Field(description="发布状态（published/withdrawn）")
    operator_id: int | None = Field(default=None, description="操作人用户 ID")
    operator_name: str | None = Field(default=None, description="操作人用户名")
    metadata_json: dict | None = Field(default=None, description="扩展元数据（维护参数/受众/强推快照）")
    published_at: datetime | None = Field(default=None, description="发布时间")
    withdrawn_at: datetime | None = Field(default=None, description="撤回时间")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="最近更新时间")


class PublishResultResponse(SystemNotificationResponse):
    """发布/重新发布结果响应（通知详情 + 强推成功用户数 + 幂等命中标记）。"""

    sent_count: int = Field(default=0, description="多渠道强推成功用户数")
    idempotent: bool = Field(default=False, description="是否命中幂等键直接返回首次结果")


class OperationResponse(BaseModel):
    """通用操作结果响应。"""

    message: str = Field(description="操作结果文案")


class SystemNotificationConfigResponse(BaseModel):
    """系统通知渠道配置响应。"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="配置 ID")
    channel: str = Field(description="渠道标识（email/dingtalk/feishu/station/sms）")
    config: dict = Field(default_factory=dict, description="渠道配置对象")
    enabled: bool = Field(description="是否启用")


class ChannelTestResponse(BaseModel):
    """渠道测试发送结果响应。"""

    success: bool = Field(description="是否发送成功")
    error: str | None = Field(default=None, description="失败提示（统一文案，不暴露底层细节）")


class SystemNoticeDeliveryItemResponse(BaseModel):
    """系统通知投递明细项。"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="投递明细 ID")
    user_id: int | None = Field(default=None, description="接收用户 ID")
    channel: str = Field(description="投递渠道")
    recipient: str = Field(description="接收人标识")
    status: str = Field(description="投递状态（pending/success/failed）")
    retry_count: int = Field(default=0, description="已重试次数")
    max_retries: int = Field(default=0, description="最大重试次数")
    error_message: str | None = Field(default=None, description="最近一次错误信息")
    receive_at: datetime | None = Field(default=None, description="送达时间")
    created_at: datetime | None = Field(default=None, description="创建时间")


class SystemNoticeDeliveryListResponse(BaseModel):
    """系统通知投递明细分页响应（含状态统计）。"""

    items: list[SystemNoticeDeliveryItemResponse] = Field(default_factory=list, description="投递明细列表")
    total: int = Field(default=0, description="总条数")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=20, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")
    stats: dict[str, int] = Field(default_factory=dict, description="按投递状态统计（pending/success/failed...）")


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
    对应 system_notification_configs 表的 config 与 enabled 字段。
    """

    config: dict = Field(default_factory=dict, description="渠道配置对象（webhook 地址、密钥等）")
    enabled: bool = Field(default=True, description="是否启用该渠道")
