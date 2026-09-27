#!/usr/bin/env python3
"""
个人中心接口

当前登录用户的自我服务接口：查看/修改自己的资料、改密码、
获取自己的菜单树、管理自己的通知偏好与接收人。

Endpoints:
    GET    /profile/me:                        获取当前用户信息
    PUT    /profile/me:                        修改个人信息
    POST   /profile/change-password:            修改密码
    GET    /profile/menus:                     获取当前用户菜单树
    GET    /profile/notification-preferences:  获取我的通知偏好
    PUT    /profile/notification-preferences:  更新我的通知偏好
    GET    /profile/notification-recipients:   获取我的通知接收人列表
    POST   /profile/notification-recipients:   添加通知接收人
    PUT    /profile/notification-recipients/{id}:  更新通知接收人
    DELETE /profile/notification-recipients/{id}: 删除通知接收人
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import (
    get_current_user,
    get_notification_dispatcher,
    get_station_service,
    get_user_service,
)
from src.api.response import success_response
from src.models.entities.menu_entity import MenuEntity
from src.notification.dispatcher import NotificationDispatcher
from src.schemas.auth import CurrentUser
from src.schemas.profile import ChangePasswordRequest, UpdateMeRequest
from src.services.station_service import StationMessageService
from src.services.user_service import UserService

router = APIRouter(prefix="/profile", tags=["个人中心"])


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
    # 查角色列表（经仓库）
    roles = user_service._repository.get_roles_by_user_id(current_user.id)
    data["roles"] = [{"id": r.id, "name": r.role_name, "code": r.role_code} for r in roles]

    # 查权限详情（带模块和名称）
    if "*" not in current_user.permissions:
        role_ids = [r.id for r in roles]
        perms = user_service._repository.get_permissions_by_role_ids(role_ids)
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
    user_service._repository.commit()
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
    station_service: StationMessageService = Depends(get_station_service),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
):
    """修改当前用户密码。"""
    from src.utils.security import verify_password, hash_password
    from datetime import datetime

    user = user_service._repository.get_by_id(current_user.id)
    if user is None:
        from src.core.exceptions import NotFoundException
        raise NotFoundException(message="用户不存在")
    if not verify_password(body.old_password, user.password_hash or ""):
        from src.core.exceptions import ValidationException
        raise ValidationException(message="原密码错误")
    user.password_hash = hash_password(body.new_password)
    user_service._repository.commit()

    # 发站内信
    try:
        station_service.send_station(
            user_id=current_user.id,
            title="密码已修改",
            content=f"您的密码已于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 修改",
        )
    except Exception:
        pass

    # 发邮件
    try:
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
    "openapi_app.created": "开放平台应用创建",
    "openapi_app.updated": "开放平台应用更新",
    "openapi_app.deleted": "开放平台应用删除",
    "openapi_app.key_reset": "AppKey重置",
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
