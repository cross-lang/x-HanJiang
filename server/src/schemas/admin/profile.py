#!/usr/bin/env python3
"""个人中心请求/响应 Schema。
集中定义个人中心（/api/v1/profile）各接口的入参模型，
由 API 层完成格式校验后透传给 ProfileService。

Classes:
    UpdateMeRequest: 修改个人信息入参
    ChangePasswordRequest: 修改密码入参
    UpdateNotificationPreferencesRequest: 更新通知偏好入参
    NotificationRecipientCreateRequest: 新增通知接收人入参
    NotificationRecipientUpdateRequest: 更新通知接收人入参（部分字段）
    UpdatePhoneRequest: 修改手机号入参
    UpdateEmailRequest: 修改邮箱入参
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from src.utils.time import normalize_date_str


class UpdateMeRequest(BaseModel):
    """修改个人信息入参。"""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    gender: str | None = None
    birthday: str | None = None

    @field_validator("birthday", mode="before")
    @classmethod
    def parse_birthday(cls, v: object) -> str | None:
        """将生日输入规范化为本地日期 YYYY-MM-DD（兼容 ISO datetime，时区换算避免差一天）。

        Args:
            v: birthday 原始输入（str / date / datetime / None）

        Returns:
            str | None: 归一化后的日期字符串

        Raises:
            ValueError: 无法识别的日期格式
        """
        return normalize_date_str(v)


class ChangePasswordRequest(BaseModel):
    """修改密码入参（需原密码 + 验证码二次认证）。"""

    old_password: str
    new_password: str
    code: str = ""


class UpdateNotificationPreferencesRequest(BaseModel):
    """更新通知偏好入参。
    请求体直接为 {event_type: {channel: enabled}} 结构，例如
    {"user.password_changed": {"station": true, "email": false}}；
    通过前置校验器将顶层字典包装为 prefs 字段，保持与旧接口一致。
    """

    prefs: dict[str, dict[str, bool]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _wrap_top_level_dict(cls, value: object) -> object:
        """将顶层事件×渠道字典包装为 prefs 字段。

        Args:
            value: 原始请求体（应为 {event_type: {channel: enabled}}）

        Returns:
            object: 包装后的 {"prefs": value}
        """
        if isinstance(value, dict) and "prefs" not in value:
            return {"prefs": value}
        return value


class NotificationRecipientCreateRequest(BaseModel):
    """新增通知接收人入参。"""

    channel: str
    recipient: str
    label: str = ""
    enabled: bool = True


class NotificationRecipientUpdateRequest(BaseModel):
    """更新通知接收人入参（全部字段可选，仅更新传入字段）。"""

    channel: str | None = None
    recipient: str | None = None
    label: str | None = None
    enabled: bool | None = None


class UpdatePhoneRequest(BaseModel):
    """修改手机号入参（需验证码二次认证）。"""

    phone: str
    code: str


class UpdateEmailRequest(BaseModel):
    """修改邮箱入参（需原验证码二次认证）。"""

    email: str
    code: str
