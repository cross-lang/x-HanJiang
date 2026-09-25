#!/usr/bin/env python3
"""开放平台示例接口——ping。

调用方必须带 X-App-Id / X-App-Key，且应用具备 scope "ping:read"。
用于联调、连通性验证和文档示例。
"""

from fastapi import APIRouter, Request

from src.api.dependencies import CurrentApp, require_app_scope
from src.api.response import success_response

router = APIRouter(tags=["开放平台：示例"])


@router.get("/ping", summary="开放接口 ping")
async def ping(
    request: Request,
    app: CurrentApp = require_app_scope("ping:read"),
):
    """返回当前调用方应用身份，用于联调验证。"""
    return success_response(
        {
            "message": "pong",
            "app_id": app.app_id,
            "app_name": app.name,
            "scopes": app.scopes,
            "auth_mode": app.auth_mode,
        },
        request,
    )
