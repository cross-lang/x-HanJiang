#!/usr/bin/env python3
"""账号安全与 MFA 接口。"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import get_current_user, get_mfa_service
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.services.mfa_service import MFAService

router = APIRouter(prefix="/security", tags=["security"])


@router.get(
    "/mfa/setup",
    summary="生成 MFA 配置",
    description="生成 TOTP MFA 的 secret 和 otpauth 链接",
)
async def setup_mfa(
    request: Request,
    current_user: CurrentUserResponse = Depends(get_current_user),
    service: MFAService = Depends(get_mfa_service),
):
    secret = service.generate_secret()
    return success_response(
        {
            "secret": secret,
            "otpauth_url": service.build_otpauth_url(current_user.username, secret),
        },
        request,
    )


@router.post(
    "/mfa/verify",
    summary="校验 MFA 代码",
    description="校验当前时间窗口的 TOTP 6 位动态码",
)
async def verify_mfa(
    request: Request,
    code: str,
    secret: str,
    service: MFAService = Depends(get_mfa_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    result = service.verify_code(secret, code)
    return success_response({"verified": result}, request)
