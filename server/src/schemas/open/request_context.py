#!/usr/bin/env python3
"""开放接口请求鉴权上下文（网关域 DTO）。

由 API 层（src/api/dependencies.get_current_app）从 FastAPI Request
剥离为纯数据后传入网关服务，使 services 层不依赖 Web 框架对象：
- HTTP 方法 / URI / 请求体：签名串重算所需；
- X-App-Id / X-App-Key / X-App-Authorization / X-App-Date：鉴权凭证。
"""

from pydantic import BaseModel, Field


class OpenApiAuthContext(BaseModel):
    """开放接口单次请求的鉴权上下文（纯数据，无框架依赖）。"""

    app_id: str = Field(description="X-App-Id：应用标识")
    plain_key: str | None = Field(default=None, description="X-App-Key：明文凭证（plain/both 模式）")
    authorization: str | None = Field(
        default=None,
        description="X-App-Authorization：HanJiang-1 签名，格式 'HanJiang-1 {app_id}:{signature}'（hmac/both 模式）",
    )
    date: str | None = Field(default=None, description="X-App-Date：RFC1123 GMT 时间（签名时间窗校验）")
    method: str = Field(description="HTTP 方法（GET/POST/PUT/PATCH/DELETE）")
    uri: str = Field(description="完整路径 + 查询串（不含域名，含 /api/open/v1 前缀）")
    body: bytes = Field(default=b"", description="请求体字节流（参与签名串 SHA256 计算）")
