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
    user_service: UserService = Depends(get_user_service),
):
    """当前用户信息接口。"""
    data = current_user.model_dump()
    # 查角色列表
    db = user_service._repository.session
    from src.models.entities.user_entity import UserRoleEntity, RoleEntity, PermissionEntity
    roles = db.query(RoleEntity).join(
        UserRoleEntity, UserRoleEntity.role_id == RoleEntity.id
    ).filter(UserRoleEntity.user_id == current_user.id).all()
    data["roles"] = [{"id": r.id, "name": r.role_name, "code": r.role_code} for r in roles]

    # 查权限详情（带模块和名称）
    if "*" not in current_user.permissions:
        from src.models.entities.user_entity import RolePermissionEntity
        role_ids = [r.id for r in roles]
        perms = db.query(PermissionEntity).join(
            RolePermissionEntity, RolePermissionEntity.permission_id == PermissionEntity.id
        ).filter(
            RolePermissionEntity.role_id.in_(role_ids),
            PermissionEntity.is_deprecated == 0,
        ).order_by(PermissionEntity.sort_order).all()
        data["permission_list"] = [
            {"code": p.perm_code, "name": p.perm_name, "module": p.module}
            for p in perms
        ]
    else:
        data["permission_list"] = []
    return success_response(data, request)


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
        if v is None or v == '' or not hasattr(user, k):
            continue
        # birthday 是 date 类型，前端传的是 ISO datetime，截取前10位 YYYY-MM-DD
        if k == 'birthday' and isinstance(v, str) and len(v) >= 10:
            v = v[:10]
        setattr(user, k, v)
    user_service._repository.session.commit()
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
    user_service._repository.session.commit()

    # 发站内信
    try:
        from src.services.station_service import StationMessageService
        from datetime import datetime
        StationMessageService().send_station(
            user_id=current_user.id,
            title="密码已修改",
            content=f"您的密码已于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 修改",
        )
    except Exception:
        pass

    # 发邮件
    try:
        from src.notification.dispatcher import NotificationDispatcher
        from src.infras.notification import get_registry
        from src.infras.database import get_cached_database_provider
        from datetime import datetime
        db = get_cached_database_provider().get_session_factory()()
        dispatcher = NotificationDispatcher(registry=get_registry(), session=db)
        dispatcher.dispatch(
            event_type="user.password_changed",
            recipients={"email": user.email},
            variables={
                "username": user.name or user.username,
                "changed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )
    except Exception:
        pass

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


# ── 个人通知偏好 ────────────────────────────────────────────

NOTIFICATION_EVENT_LABELS = {
    "user.password_changed": "修改密码",
    "user.profile_updated": "个人资料修改",
    "user.created": "新用户创建",
    "user.deleted": "账号删除",
    "role.assigned": "角色变更",
    "file.uploaded": "文件上传",
    "file.deleted": "文件删除",
    "file.downloaded": "文件下载",
    "app.created": "应用创建",
    "app.updated": "应用更新",
    "app.deleted": "应用删除",
    "app.key_reset": "AppKey重置",
    "login.new_device": "新设备登录",
}

CHANNEL_LABELS = {
    "station": "站内信",
    "email": "邮件",
    "dingtalk": "钉钉",
    "feishu": "飞书",
}


@router.get(
    "/notification-preferences",
    summary="获取我的通知偏好",
)
async def get_my_preferences(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    from src.models.entities.notification_preference_entity import UserNotificationPreferenceEntity
    from src.infras.database import get_cached_database_provider
    db = get_cached_database_provider().get_session_factory()()
    rows = db.query(UserNotificationPreferenceEntity).filter(
        UserNotificationPreferenceEntity.user_id == current_user.id
    ).all()
    # 转成 {event: {channel: enabled}} 结构
    prefs = {}
    for r in rows:
        if r.event_type not in prefs:
            prefs[r.event_type] = {}
        prefs[r.event_type][r.channel] = r.enabled

    # 返回完整列表（含所有事件和渠道）
    events = []
    for event_code, event_name in NOTIFICATION_EVENT_LABELS.items():
        channels = []
        for ch_code, ch_name in CHANNEL_LABELS.items():
            channels.append({
                "code": ch_code,
                "name": ch_name,
                "enabled": prefs.get(event_code, {}).get(ch_code, ch_code == "station"),  # 默认站内信开
            })
        events.append({
            "event": event_code,
            "name": event_name,
            "channels": channels,
        })
    return success_response({"events": events}, request)


@router.put(
    "/notification-preferences",
    summary="更新我的通知偏好",
)
async def update_my_preferences(
    request: Request,
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
):
    """body: {event_type: {channel: enabled}}"""
    from src.models.entities.notification_preference_entity import UserNotificationPreferenceEntity
    from src.infras.database import get_cached_database_provider
    db = get_cached_database_provider().get_session_factory()()
    for event_type, channels in body.items():
        for channel, enabled in channels.items():
            row = db.query(UserNotificationPreferenceEntity).filter(
                UserNotificationPreferenceEntity.user_id == current_user.id,
                UserNotificationPreferenceEntity.event_type == event_type,
                UserNotificationPreferenceEntity.channel == channel,
            ).first()
            if row:
                row.enabled = enabled
            else:
                row = UserNotificationPreferenceEntity(
                    user_id=current_user.id,
                    event_type=event_type,
                    channel=channel,
                    enabled=enabled,
                )
                db.add(row)
    db.commit()
    return success_response({"updated": True}, request)


# ── 个人通知接收人管理 ────────────────────────────────────

@router.get(
    "/notification-recipients",
    summary="获取我的通知接收人列表",
)
async def get_my_recipients(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    from src.models.entities.notification_recipient_entity import NotificationRecipientEntity
    from src.infras.database import get_cached_database_provider
    db = get_cached_database_provider().get_session_factory()()
    rows = db.query(NotificationRecipientEntity).filter(
        NotificationRecipientEntity.user_id == current_user.id
    ).order_by(NotificationRecipientEntity.channel, NotificationRecipientEntity.id).all()
    return success_response({
        "items": [{
            "id": r.id,
            "channel": r.channel,
            "recipient": r.recipient,
            "label": r.label,
            "enabled": r.enabled,
        } for r in rows]
    }, request)


@router.post(
    "/notification-recipients",
    summary="添加通知接收人",
)
async def add_recipient(
    request: Request,
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
):
    from src.models.entities.notification_recipient_entity import NotificationRecipientEntity
    from src.infras.database import get_cached_database_provider
    db = get_cached_database_provider().get_session_factory()()
    row = NotificationRecipientEntity(
        user_id=current_user.id,
        channel=body["channel"],
        recipient=body["recipient"],
        label=body.get("label", ""),
        enabled=body.get("enabled", True),
    )
    db.add(row)
    db.commit()
    return success_response({"id": row.id}, request, code=201)


@router.put(
    "/notification-recipients/{recipient_id}",
    summary="更新通知接收人",
)
async def update_recipient(
    recipient_id: int,
    request: Request,
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
):
    from src.models.entities.notification_recipient_entity import NotificationRecipientEntity
    from src.infras.database import get_cached_database_provider
    db = get_cached_database_provider().get_session_factory()()
    row = db.query(NotificationRecipientEntity).filter(
        NotificationRecipientEntity.id == recipient_id,
        NotificationRecipientEntity.user_id == current_user.id,
    ).first()
    if not row:
        from src.core.exceptions import NotFoundException
        raise NotFoundException(message="接收人不存在")
    for k in ("channel", "recipient", "label", "enabled"):
        if k in body:
            setattr(row, k, body[k])
    db.commit()
    return success_response({"updated": True}, request)


@router.delete(
    "/notification-recipients/{recipient_id}",
    summary="删除通知接收人",
)
async def delete_recipient(
    recipient_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    from src.models.entities.notification_recipient_entity import NotificationRecipientEntity
    from src.infras.database import get_cached_database_provider
    db = get_cached_database_provider().get_session_factory()()
    row = db.query(NotificationRecipientEntity).filter(
        NotificationRecipientEntity.id == recipient_id,
        NotificationRecipientEntity.user_id == current_user.id,
    ).first()
    if not row:
        from src.core.exceptions import NotFoundException
        raise NotFoundException(message="接收人不存在")
    db.delete(row)
    db.commit()
    return success_response({"deleted": True}, request)
