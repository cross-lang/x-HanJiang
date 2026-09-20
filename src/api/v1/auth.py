#!/usr/bin/env python3
"""
认证接口

本模块提供登录、令牌刷新、当前用户信息查询、退出登录、密码重置接口。

Endpoints:
    POST /auth/login:              用户名或邮箱 + 密码登录
    POST /auth/refresh:            刷新令牌
    GET  /auth/me:                 获取当前登录用户信息
    POST /auth/logout:             退出登录（清除 Redis 登录态）
    POST /auth/password-reset:     请求密码重置（发送邮件）
    POST /auth/password-reset/verify: 验证重置令牌
    POST /auth/password-reset/confirm: 确认密码重置
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import get_auth_service, get_current_user
from src.api.response import success_response
from src.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    VerifyResetTokenRequest,
    VerifyResetTokenResponse,
)
from src.services.auth_service import AuthService
from src.utils.helpers import get_client_ip

router = APIRouter(prefix="/auth", tags=["身份认证"])


@router.post(
    "/login",
    summary="用户登录",
    description="用户名或邮箱 + 密码登录，成功后返回访问/刷新令牌",
)
async def login(
    body: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """登录接口。

    登录成功/失败均会写入 login_logs 表。
    """
    ip = get_client_ip(request)
    result = service.login(
        body.username,
        body.password,
        ip_address=ip,
        client_type=body.client_type,
    )
    return success_response(result.model_dump(), request)


@router.post(
    "/refresh",
    summary="刷新令牌",
    description="使用刷新令牌换取新的访问/刷新令牌对",
)
async def refresh(
    body: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """刷新令牌接口。"""
    result = service.refresh(body.refresh_token)
    return success_response(result.model_dump(), request)


@router.get(
    "/me",
    summary="当前用户信息",
    description="获取当前登录用户信息（需 Bearer 令牌）",
)
async def me(
    request: Request,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """当前用户信息接口。"""
    return success_response(current_user.model_dump(), request)


@router.post(
    "/logout",
    summary="退出登录",
    description="清除当前用户的 Redis 登录态，使令牌立即失效（需 Bearer 令牌）",
)
async def logout(
    request: Request,
    current_user: CurrentUserResponse = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """退出登录接口。

    清除 Redis 中的 login:{user_id} 登录态，已签发的令牌立即失效。
    """
    service.logout(current_user.id)
    return success_response({"message": "退出登录成功"}, request)


@router.post(
    "/password-reset",
    summary="请求密码重置",
    description="发送密码重置邮件到用户邮箱（无需登录）",
    response_model=PasswordResetResponse,
)
async def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """请求密码重置接口。

    流程：
    1. 验证邮箱是否存在
    2. 检查频率限制（每小时最多 5 次）
    3. 生成重置令牌
    4. 发送重置邮件

    注意：即使邮箱不存在，也返回成功（防止邮箱枚举攻击）。
    """
    try:
        service.request_password_reset(body.email)
    except Exception:
        # 即使失败也返回成功，防止邮箱枚举
        pass

    return success_response(
        PasswordResetResponse(
            message="如果该邮箱已注册，您将收到密码重置邮件",
            success=True,
        ).model_dump(),
        request,
    )


@router.post(
    "/password-reset/verify",
    summary="验证重置令牌",
    description="验证密码重置令牌是否有效（无需登录）",
    response_model=VerifyResetTokenResponse,
)
async def verify_reset_token(
    body: VerifyResetTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """验证重置令牌接口。

    用于前端在用户点击邮件链接后，验证令牌是否有效。
    """
    result = service.verify_reset_token(body.token)
    return success_response(
        VerifyResetTokenResponse(**result).model_dump(),
        request,
    )


@router.post(
    "/password-reset/confirm",
    summary="确认密码重置",
    description="使用重置令牌设置新密码（无需登录）",
    response_model=PasswordResetResponse,
)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """确认密码重置接口。

    流程：
    1. 验证令牌
    2. 验证两次密码输入一致
    3. 更新密码
    4. 撤销令牌
    5. 清除登录态（强制重新登录）
    """
    # 验证两次密码输入一致
    if body.new_password != body.confirm_password:
        from src.core.exceptions import ValidationException
        raise ValidationException(message="两次密码输入不一致")

    # 执行密码重置
    service.reset_password(body.token, body.new_password)

    return success_response(
        PasswordResetResponse(
            message="密码重置成功，请使用新密码登录",
            success=True,
        ).model_dump(),
        request,
    )
