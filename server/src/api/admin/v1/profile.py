#!/usr/bin/env python3
"""
个人中心接口（API 接入层）
当前登录用户的自我服务接口：查看/修改自己的资料、改密码、
获取自己的菜单树、管理自己的通知偏好与接收人、安全设置。
分层约束：
    本层仅接收参数并调用 ProfileService，不实现业务逻辑、不直接操作数据库；
    参数格式校验由 schemas/ 完成，业务规则校验由 services/ 完成。

Endpoints:
    GET    /profile/me:                        获取当前用户信息
    PUT    /profile/me:                        修改个人信息
    POST   /profile/change-password:            修改密码
    GET    /profile/menus:                     获取当前用户菜单树
    GET    /profile/notification-preferences:  获取我的通知偏好（事件×渠道开关）
    PUT    /profile/notification-preferences:  更新我的通知偏好
    GET    /profile/notification-recipients:  获取我的渠道接收方（每个渠道一个 recipient）
    POST   /profile/notification-recipients:  保存渠道接收方（upsert）
    PUT    /profile/notification-recipients:  更新渠道接收方（upsert）
    DELETE /profile/notification-recipients:  清空渠道接收方并禁用该渠道
    POST   /profile/send-verify-code:          发送验证码
    POST   /profile/update-phone:              修改手机号
    POST   /profile/update-email:              修改邮箱
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_current_user,
    get_profile_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.profile import (
    ChangePasswordRequest,
    NotificationRecipientCreateRequest,
    NotificationRecipientUpdateRequest,
    UpdateEmailRequest,
    UpdateMeRequest,
    UpdateNotificationPreferencesRequest,
    UpdatePhoneRequest,
)
from src.services.admin.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["管理系统：个人中心"])


@router.get(
    "/me",
    summary="当前用户信息",
    description="获取当前登录用户信息（需 Bearer 令牌）",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_VIEW.mark))],
)
@permission(PermissionCode.PROFILE_VIEW)
def me(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """当前用户信息接口。"""
    return success_response(profile_service.get_my_profile(current_user), request)


@router.put(
    "/me",
    summary="修改个人信息",
    description="当前用户修改自己的基本信息（不能修改登录名）",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def update_me(
    body: UpdateMeRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """修改当前用户个人信息。"""
    profile_service.update_my_profile(current_user.id, body)
    return success_response({"message": "修改成功"}, request)


@router.post(
    "/change-password",
    summary="修改密码",
    description="当前用户修改自己的密码（需提供原密码 + 验证码二次认证）",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_PASSWORD.mark))],
)
@permission(PermissionCode.PROFILE_PASSWORD)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """修改当前用户密码。"""
    profile_service.change_password(current_user.id, body)
    return success_response({"message": "密码修改成功"}, request)


@router.get(
    "/menus",
    summary="当前用户菜单树",
    description="根据当前用户权限返回可见菜单树",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_VIEW.mark))],
)
@permission(PermissionCode.PROFILE_VIEW)
def get_menus(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """返回当前用户可见的菜单树。"""
    return success_response(profile_service.get_my_menus(current_user), request)


# ── 个人通知偏好 ────────────────────────────────────────────


@router.get(
    "/notification-preferences",
    summary="获取我的通知偏好",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_VIEW.mark))],
)
@permission(PermissionCode.PROFILE_VIEW)
def get_my_preferences(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """获取当前用户的完整通知偏好（含所有事件和渠道）。"""
    return success_response(profile_service.get_notification_preferences(current_user.id), request)


@router.put(
    "/notification-preferences",
    summary="更新我的通知偏好",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def update_my_preferences(
    request: Request,
    body: UpdateNotificationPreferencesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """更新当前用户的通知偏好。"""
    profile_service.update_notification_preferences(current_user.id, body.prefs)
    return success_response({"updated": True}, request)


# ── 个人通知接收人管理 ────────────────────────────────────


@router.get(
    "/notification-recipients",
    summary="获取我的渠道接收方",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_VIEW.mark))],
)
@permission(PermissionCode.PROFILE_VIEW)
def get_my_recipients(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """获取当前用户各渠道的接收方（按渠道聚合，每个渠道一个 recipient）。"""
    return success_response(profile_service.get_recipients(current_user.id), request)


@router.post(
    "/notification-recipients",
    summary="保存渠道接收方",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def add_recipient(
    request: Request,
    body: NotificationRecipientCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """保存当前用户某渠道的接收方（单值，upsert；同步刷新该渠道下所有事件行）。"""
    profile_service.add_recipient(current_user.id, body)
    return success_response({"updated": True}, request, code=201)


@router.put(
    "/notification-recipients",
    summary="更新渠道接收方",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def update_recipient(
    request: Request,
    body: NotificationRecipientUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """更新当前用户某渠道的接收方（单值，upsert；同步刷新该渠道下所有事件行）。"""
    profile_service.update_recipient(current_user.id, body)
    return success_response({"updated": True}, request)


@router.delete(
    "/notification-recipients",
    summary="清空渠道接收方",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def delete_recipient(
    channel: str,
    recipient: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """清空当前用户某渠道的接收方并禁用该渠道（recipient 参数保留兼容，后端按 channel 清空）。"""
    profile_service.delete_recipient(current_user.id, channel, recipient)
    return success_response({"deleted": True}, request)


@router.post(
    "/notification-recipients/test",
    summary="测试我的 Webhook",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def test_my_recipient(
    request: Request,
    channel: str = Query(..., description="渠道标识（dingtalk / feishu）"),
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """用当前用户自己配置的钉钉/飞书 Webhook 发一条测试消息，验证连通性。"""
    result = profile_service.test_recipient(current_user.id, channel)
    return success_response(result, request)


# ── 安全设置：邮箱二次认证 ──────────────────────────────────


@router.post(
    "/send-verify-code",
    summary="发送验证码",
    description="安全设置二次认证：向当前用户邮箱发送 6 位验证码，5 分钟有效",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EDIT.mark))],
)
@permission(PermissionCode.PROFILE_EDIT)
def send_verify_code(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """向当前用户邮箱发送验证码。"""
    profile_service.send_verify_code(current_user.id)
    return success_response({"message": "验证码已发送至邮箱"}, request)


@router.post(
    "/update-phone",
    summary="修改手机号",
    description="需通过验证码二次认证",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_PHONE.mark))],
)
@permission(PermissionCode.PROFILE_PHONE)
def update_phone(
    request: Request,
    body: UpdatePhoneRequest,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """通过验证码校验后修改手机号。"""
    profile_service.verify_and_update_phone(current_user.id, body.code, body.phone)
    return success_response({"message": "手机号修改成功"}, request)


@router.post(
    "/update-email",
    summary="修改邮箱",
    description="需通过原验证码二次认证",
    dependencies=[Depends(require_user_permission(PermissionCode.PROFILE_EMAIL.mark))],
)
@permission(PermissionCode.PROFILE_EMAIL)
def update_email(
    request: Request,
    body: UpdateEmailRequest,
    current_user: CurrentUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> JSONResponse:
    """通过原验证码校验后修改邮箱。"""
    profile_service.verify_and_update_email(current_user.id, body.code, body.email)
    return success_response({"message": "邮箱修改成功"}, request)
