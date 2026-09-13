#!/usr/bin/env python3
"""业务审计日志响应模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """审计日志响应模型。"""

    id: int = Field(description="审计日志唯一标识")
    entity_type: str = Field(description="被操作的数据类型")
    entity_id: str | None = Field(default=None, description="被操作的数据ID")
    action: str = Field(description="操作类型")
    operator_id: int | None = Field(default=None, description="操作人用户ID")
    operator_name: str | None = Field(default=None, description="操作人用户名")
    before_data: dict[str, Any] | None = Field(default=None, description="变更前数据")
    after_data: dict[str, Any] | None = Field(default=None, description="变更后数据")
    ip_address: str | None = Field(default=None, description="操作来源IP地址")
    created_at: datetime | None = Field(default=None, description="记录创建时间")
    remarks: str | None = Field(default=None, description="备注")

    model_config = ConfigDict(from_attributes=True)
