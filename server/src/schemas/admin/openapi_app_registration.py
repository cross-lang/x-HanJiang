#!/usr/bin/env python3
"""开放平台应用申请（审批批次）DTO（管理端视角）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppRegistrationApprovalRequest(BaseModel):
    """审批应用申请请求（通过 / 驳回）。"""

    approved: bool = Field(description="是否通过（true 通过 / false 驳回）")
    note: str | None = Field(default=None, max_length=255, description="审批意见/驳回原因（驳回建议填写）")


class AppRegistrationResponse(BaseModel):
    """应用申请（审批批次）列表/详情响应。

    每次创建/修改申请为一条记录，以 registration_code（申请码）对外展示，
    id 仅作为内部主键区分不同批次。
    """

    id: int
    registration_code: str
    app_id: int
    app_id_str: str
    app_name: str
    owner_name: str | None = None
    owner_type: str
    registration_type: str
    name: str
    description: str
    scopes: list[str]
    auth_mode: str
    apply_reason: str | None = None
    status: str
    approved_by: int | None = None
    approval_note: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
