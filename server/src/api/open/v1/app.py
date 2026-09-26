#!/usr/bin/env python3
"""开放平台当前应用信息接口。

参考用户态 /api/v1/auth/me，返回当前调用方应用身份。
不需要特定 scope——任何有效应用都能查询自己的信息。
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import CurrentApp, get_current_app
from src.api.response import success_response

router = APIRouter(tags=["开放平台：应用信息"])


@router.get("/me", summary="当前应用信息")
async def me(
    request: Request,
    app: CurrentApp = Depends(get_current_app),
):
    """返回当前调用方应用信息（需 X-App-Id / X-App-Key）。"""
    return success_response(app.model_dump(), request)
