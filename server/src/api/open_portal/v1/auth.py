#!/usr/bin/env python3
"""开放平台门户开发者认证接口（门户会话 JWT + Redis，对齐管理系统 /api/admin/v1/auth）。
路由前缀：/api/open-portal/v1/auth
说明：开发者账号存 developers 表（与管理系统 users 分表）；
     登录态为有状态会话（JWT + Redis），登出/修改密码后旧令牌即失效。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.open_portal.dependencies import (
    get_current_developer,
    get_developer_auth_service,
)
from src.api.response import success_response
from src.schemas.open_portal.auth import (
    CurrentDeveloper,
    DeveloperChangePasswordRequest,
    DeveloperForgotPasswordRequest,
    DeveloperLoginRequest,
    DeveloperRefreshRequest,
    DeveloperRegisterRequest,
    DeveloperResetPasswordRequest,
)
from src.services.open_portal.auth_service import DeveloperAuthService

router = APIRouter(prefix="/auth", tags=["开放平台：身份认证"])


@router.post(
    "/register",
    summary="开发者注册",
    description="注册开放平台门户账号（用户名/邮箱全局唯一，与管理系统用户分表）",
)
def register(
    body: DeveloperRegisterRequest,
    request: Request,
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    data = service.register(
        username=body.username,
        email=body.email,
        password=body.password,
        confirm_password=body.confirm_password,
        name=body.name,
        certification_type=body.certification_type,
    )
    return success_response(data.model_dump(), request, code=201)


@router.post(
    "/login",
    summary="开发者登录",
    description="账号=用户名或邮箱 + 密码，签发 access/refresh 令牌对并建立服务端登录态",
)
def login(
    body: DeveloperLoginRequest,
    request: Request,
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    return success_response(service.login(body.account, body.password).model_dump(), request)


@router.post(
    "/refresh",
    summary="刷新令牌",
    description="用 refresh_token 换取新令牌对；旧 access 令牌随 Redis 登录态轮换而失效",
)
def refresh(
    body: DeveloperRefreshRequest,
    request: Request,
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    return success_response(service.refresh(body.refresh_token).model_dump(), request)


@router.post(
    "/logout",
    summary="开发者退出登录",
    description="清除服务端登录态（Redis），当前已签发的全部访问令牌立即失效",
)
def logout(
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    service.logout(current_developer.id)
    return success_response({"logged_out": True}, request)


@router.post(
    "/change-password",
    summary="修改密码",
    description="校验原密码后更新密码哈希，并撤销服务端登录态（修改成功后需重新登录）",
)
def change_password(
    body: DeveloperChangePasswordRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    service.change_password(current_developer.id, body.old_password, body.new_password)
    return success_response({"changed": True}, request)


@router.post(
    "/forgot-password",
    summary="忘记密码：发送重置邮件",
    description="提交注册邮箱，向邮箱发送含一次性重置令牌的邮件（30 分钟有效）。"
    "邮箱未注册时同样返回成功提示，避免账号枚举",
)
def forgot_password(
    body: DeveloperForgotPasswordRequest,
    request: Request,
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    return success_response(service.request_password_reset(body.email), request)


@router.post(
    "/reset-password",
    summary="重置密码（邮箱二次认证）",
    description="携带邮件中的重置令牌 + 新密码完成重置；重置后撤销全部登录态并作废令牌",
)
def reset_password(
    body: DeveloperResetPasswordRequest,
    request: Request,
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    service.reset_password(body.token, body.new_password, body.confirm_password)
    return success_response({"reset": True}, request)
