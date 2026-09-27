#!/usr/bin/env python3
"""
认证接口

本模块提供管理后台核心认证接口。

Endpoints:
    POST /auth/login:    用户名/邮箱 + 密码登录
    POST /auth/refresh:  刷新令牌
    POST /auth/logout:   退出登录
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_notification_dispatcher,
)
from src.api.response import success_response
from src.schemas.auth import (
    CurrentUser,
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
    # 新设备登录检测：查最近登录日志，IP不同则发邮件
    try:
        from src.models.entities.login_log_entity import LoginLogEntity
        from src.infras.database import get_cached_database_provider
        from src.api.dependencies import get_notification_dispatcher
        from src.constants.enums import NotificationEvent
        db = get_cached_database_provider().get_session_factory()()
        # 查该用户最近一次成功登录的IP
        last = db.query(LoginLogEntity).filter(
            LoginLogEntity.user_id == result.user_id,
            LoginLogEntity.status == "success",
        ).order_by(LoginLogEntity.created_at.desc()).offset(1).first()
        if last and last.ip_address != ip:
            get_notification_dispatcher().dispatch_for_user(
                user_id=result.user_id,
                event_type=NotificationEvent.LOGIN_NEW_DEVICE,
                variables={"ip": ip, "time": result.login_time if hasattr(result, 'login_time') else ""},
            )
    except Exception:
        pass
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


@router.post(
    "/logout",
    summary="退出登录",
    description="清除当前用户的 Redis 登录态，使令牌立即失效（需 Bearer 令牌）",
)
async def logout(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """退出登录接口。

    清除 Redis 中的 login:{user_id} 登录态，已签发的令牌立即失效。
    """
    service.logout(current_user.id)
    return success_response({"message": "退出登录成功"}, request)
