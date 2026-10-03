#!/usr/bin/env python3
"""开放平台开发者认证接口（门户 JWT，与管理端 /api/v1/auth 平行）。
路由前缀：/api/open/v1/auth
说明：开发者账号存 developers 表（与管理系统 users 分表），令牌复用 core.tokens。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_current_developer,
    get_developer_auth_service,
)
from src.api.response import success_response
from src.schemas.open.auth import (
    CurrentDeveloper,
    DeveloperChangePasswordRequest,
    DeveloperLoginRequest,
    DeveloperRegisterRequest,
)
from src.services.open.auth_service import DeveloperAuthService

router = APIRouter(prefix="/auth", tags=["开放平台：开发者认证"])


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
        certification_type=body.certification_type,
    )
    return success_response(data.model_dump(), request, code=201)


@router.post(
    "/login",
    summary="开发者登录",
    description="账号=用户名或邮箱 + 密码，返回 Bearer 访问令牌（存于 web/open 前端）",
)
def login(
    body: DeveloperLoginRequest,
    request: Request,
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    return success_response(service.login(body.account, body.password).model_dump(), request)


@router.post(
    "/logout",
    summary="开发者退出登录",
    description="无服务端会话（JWT 无状态），由前端清除本地令牌；端点幂等返回成功",
)
def logout(request: Request) -> JSONResponse:
    return success_response({"logged_out": True}, request)


@router.post(
    "/change-password",
    summary="修改密码",
    description="校验原密码后更新密码哈希；修改成功后前端应引导重新登录",
)
def change_password(
    body: DeveloperChangePasswordRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> JSONResponse:
    service.change_password(current_developer.id, body.old_password, body.new_password)
    return success_response({"changed": True}, request)
