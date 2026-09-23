#!/usr/bin/env python3
"""
认证接口

本模块提供管理后台核心认证接口。

Endpoints:
    POST /auth/login:      用户名/邮箱 + 密码登录
    POST /auth/refresh:    刷新令牌
    GET  /auth/me:         获取当前登录用户信息
    POST /auth/logout:     退出登录
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import get_auth_service, get_current_user
from src.api.response import success_response
from src.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
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