#!/usr/bin/env python3
"""开放 API 当前应用信息接口。
参考用户态 /api/admin/v1/auth/me，返回当前调用方应用身份。
不需要特定 scope——任何有效应用都能查询自己的信息。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.open.dependencies import get_current_app
from src.api.response import success_response
from src.schemas.common import ApiResponse
from src.schemas.open.app import CurrentApp

router = APIRouter(tags=["开放API：应用信息"])


@router.get(
    "/me",
    summary="当前开放 API 应用信息",
    response_model=ApiResponse[CurrentApp],
)
async def me(
    request: Request,
    app: CurrentApp = Depends(get_current_app),
) -> JSONResponse:
    """返回当前调用方应用信息（需 X-App-Id / X-App-Key）。"""
    return success_response(app.model_dump(), request)
