#!/usr/bin/env python3
"""开放接口（网关）域 DTO。

当前调用方应用身份（CurrentApp）：开放接口网关鉴权（AppId/Key 签名 + 审批门槛）通过后，
由 OpenGatewayService.authenticate 组装返回，作为请求上下文传递给开放接口 handler。
"""

from pydantic import BaseModel


class CurrentApp(BaseModel):
    """当前调用方应用（机器身份，无终端用户上下文）。"""

    app_id: str
    name: str
    description: str
    scopes: list[str]
    auth_mode: str
    rate_limit_per_minute: int
