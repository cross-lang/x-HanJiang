#!/usr/bin/env python3
"""开放接口告警推送 DTO（对应 api/open/v1/alert.py）。"""

from pydantic import BaseModel, Field


class AlertSendRequest(BaseModel):
    """开放 API 告警发送请求体。

    与管理端 schemas/admin/alert.py 的 AlertSendRequest 形状有意不同：
    渠道差异（开放接口 recipients 可缺省，metadata 由服务端根据调用方应用注入）。
    """

    subject: str = Field(..., description="告警标题", max_length=200)
    message: str = Field(..., description="告警内容", max_length=2000)
    recipients: dict[str, str] = Field(
        default_factory=dict,
        description='额外接收人（渠道→地址，如 {"email": "a@b.com"}），超管渠道自动追加',
    )
