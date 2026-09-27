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
from pydantic import BaseModel

from src.api.dependencies import get_auth_service, get_current_user, get_user_service
from src.models.entities.menu_entity import MenuEntity
from src.api.response import success_response
from src.schemas.auth import (
    CurrentUser,
    LoginRequest,
    RefreshTokenRequest,
)
from src.services.auth_service import AuthService
from src.services.user_service import UserService
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


class UpdateMeRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    gender: str | None = None
    birthday: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.get(
    "/me",
    summary="当前用户信息",
    description="获取当前登录用户信息（需 Bearer 令牌）",
)
async def me(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """当前用户信息接口。"""
    return success_response(current_user.model_dump(), request)


@router.put(
    "/me",
    summary="修改个人信息",
    description="当前用户修改自己的基本信息（不能修改登录名）",
)
async def update_me(
    body: UpdateMeRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """修改当前用户个人信息。"""
    user = user_service._repository.get_by_id(current_user.id)
    if user is None:
        from src.core.exceptions import NotFoundException
        raise NotFoundException(message="用户不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None and hasattr(user, k):
            setattr(user, k, v)
    user_service._commit()
    return success_response({"message": "修改成功"}, request)


@router.post(
    "/change-password",
    summary="修改密码",
    description="当前用户修改自己的密码（需提供原密码）",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """修改当前用户密码。"""
    from src.utils.security import verify_password, hash_password
    user = user_service._repository.get_by_id(current_user.id)
    if user is None:
        from src.core.exceptions import NotFoundException
        raise NotFoundException(message="用户不存在")
    if not verify_password(body.old_password, user.password_hash or ""):
        from src.core.exceptions import ValidationException
        raise ValidationException(message="原密码错误")
    user.password_hash = hash_password(body.new_password)
    user_service._commit()
    return success_response({"message": "密码修改成功"}, request)


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


@router.get(
    "/menus",
    summary="当前用户菜单树",
    description="根据当前用户权限返回可见菜单树",
)
async def get_menus(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """返回当前用户可见的菜单树。"""
    from src.infras.database import get_cached_database_provider
    from sqlalchemy import select

    session = get_cached_database_provider().get_session_factory()()
    try:
        all_menus = session.execute(
            select(MenuEntity).where(MenuEntity.status == "enabled").order_by(MenuEntity.sort_order)
        ).scalars().all()

        # 超管看到全部菜单
        if "*" in current_user.permissions:
            visible = all_menus
        else:
            visible = [m for m in all_menus if not m.perm_code or m.perm_code in current_user.permissions]

        # 构建树形结构
        menu_map = {m.id: {"id": m.id, "parent_id": m.parent_id, "title": m.title,
                           "path": m.path, "icon": m.icon, "type": m.type, "children": []}
                    for m in visible}
        tree = []
        for m in menu_map.values():
            if m["parent_id"] == 0:
                tree.append(m)
            elif m["parent_id"] in menu_map:
                menu_map[m["parent_id"]]["children"].append(m)

        # 过滤掉没有可见子菜单的目录
        def prune(nodes: list) -> list:
            result = []
            for n in nodes:
                n["children"] = prune(n["children"])
                if n["type"] == "directory" and not n["children"]:
                    continue
                result.append(n)
            return result

        tree = prune(tree)
        return success_response(tree, request)
    finally:
        session.close()