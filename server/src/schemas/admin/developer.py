#!/usr/bin/env python3
"""开放平台开发者用户管理 DTO（管理端视角）。

与管理端应用管理（schemas/admin/openapi_app.py）同域：
- 用户列表（list_developers）返回基础资料 + 旗下应用数；
- 用户旗下应用（list_developer_apps）直接复用 OpenApiAppResponse 分页结构。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeveloperAdminResponse(BaseModel):
    """开发者用户列表/详情响应（管理端）。"""

    id: int
    username: str
    email: str
    name: str
    phone: str
    certification_type: str | None
    certification_status: str
    company_name: str | None
    status: str
    app_count: int = Field(description="旗下开放应用数量（不含已软删除）")
    last_login_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


__all__ = ["DeveloperAdminResponse"]
