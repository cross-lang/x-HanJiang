#!/usr/bin/env python3
"""个人中心业务逻辑。
个人中心（/api/v1/profile）的业务规则与事务编排层：
    - 个人资料查询/修改、密码修改（邮箱验证码二次认证）
    - 当前用户菜单树组装
    - 通知偏好与通知接收人管理
    - 安全设置：验证码发送、手机号/邮箱修改
分层约束：
    - 不读取 Request / HTTP 对象，入参由 API 层解析后以参数传入；
    - 数据访问统一经 Repository，事务统一在本层提交/回滚；
    - 业务异常（NotFound/Validation）仅在本层抛出。

Classes:
    ProfileService: 个人中心业务逻辑实现
"""

from __future__ import annotations

import random
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.constants.constants import (
    DEFAULT_ENABLED_CHANNEL,
    MENU_ROOT_PARENT_ID,
    MENU_TYPE_DIRECTORY,
    VERIFY_CODE_CACHE_PREFIX,
    VERIFY_CODE_EVENT,
    VERIFY_CODE_MAX,
    VERIFY_CODE_MIN,
    VERIFY_CODE_TTL_SECONDS,
)
from src.constants.enums import NotificationChannel, NotificationEvent
from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger
from src.infras.cache import CacheProvider, get_cached_cache_provider
from src.models.entities.notification_preference_entity import UserNotificationPreferenceEntity
from src.models.entities.notification_recipient_entity import NotificationRecipientEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.menu_repository import MenuRepository
from src.repositories.notification_preference_repository import NotificationPreferenceRepository
from src.repositories.notification_recipient_repository import NotificationRecipientRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth import CurrentUser
from src.schemas.profile import (
    ChangePasswordRequest,
    NotificationRecipientCreateRequest,
    NotificationRecipientUpdateRequest,
    UpdateMeRequest,
)
from src.services.station_service import StationMessageService
from src.utils.security import hash_password, verify_password

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher


class ProfileService:
    """个人中心业务逻辑实现。"""

    def __init__(
        self,
        user_repository: UserRepository,
        menu_repository: MenuRepository,
        preference_repository: NotificationPreferenceRepository,
        recipient_repository: NotificationRecipientRepository,
        dispatcher: NotificationDispatcher | None = None,
        station_service: StationMessageService | None = None,
        cache: CacheProvider | None = None,
    ) -> None:
        """初始化个人中心服务。

        Args:
            user_repository: 用户数据访问仓库
            menu_repository: 菜单数据访问仓库
            preference_repository: 通知偏好数据访问仓库
            recipient_repository: 通知接收人数据访问仓库
            dispatcher: 通知调度器（可选，未注入时邮件通知静默跳过）
            station_service: 站内信服务（可选，未注入时站内信静默跳过）
            cache: 缓存客户端（可选，未注入时使用全局缓存提供者）
        """
        self._user_repository = user_repository
        self._menu_repository = menu_repository
        self._preference_repository = preference_repository
        self._recipient_repository = recipient_repository
        self._dispatcher = dispatcher
        self._station_service = station_service
        self._cache = cache or get_cached_cache_provider()

    # ── 个人资料 ────────────────────────────────────────────

    def get_my_profile(self, current_user: CurrentUser) -> dict[str, Any]:
        """获取当前用户资料（含角色与权限列表）。

        Args:
            current_user: 当前登录用户（API 层解析的 JWT 载荷）

        Returns:
            dict[str, Any]: 用户资料字典，包含 roles / permission_list 字段
        """
        data: dict[str, Any] = current_user.model_dump()
        roles = self._user_repository.get_roles_by_user_id(current_user.id)
        data["roles"] = [{"id": r.id, "name": r.role_name, "code": r.role_code} for r in roles]
        if "*" not in current_user.permissions:
            role_ids = [r.id for r in roles]
            perms = self._user_repository.get_permissions_by_role_ids(role_ids)
            data["permission_list"] = [{"code": p.perm_code, "name": p.perm_name, "module": p.module} for p in perms]
        else:
            data["permission_list"] = []
        return data

    def update_my_profile(self, user_id: int, request: UpdateMeRequest) -> None:
        """修改当前用户基本信息（登录名不可修改）。

        Args:
            user_id: 当前用户 ID
            request: 修改个人信息入参

        Raises:
            NotFoundException: 用户不存在时抛出
        """
        user = self._require_user(user_id)
        data = request.model_dump(exclude_unset=True)
        for key, value in data.items():
            if value is None or value == "" or not hasattr(user, key):
                continue
            # birthday 是 date 类型，前端传 ISO datetime，截取前 10 位 YYYY-MM-DD
            if key == "birthday" and isinstance(value, str) and len(value) >= 10:
                value = value[:10]
            setattr(user, key, value)
        self._user_repository.commit()

    def change_password(
        self,
        user_id: int,
        request: ChangePasswordRequest,
    ) -> None:
        """修改当前用户密码（需原密码 + 邮箱验证码二次认证）。
        成功后发送站内信与邮件通知（发送失败不阻断主流程）。

        Args:
            user_id: 当前用户 ID
            request: 修改密码入参

        Raises:
            NotFoundException: 用户不存在时抛出
            ValidationException: 原密码错误或验证码错误/过期时抛出
        """
        user = self._require_user(user_id)
        if not verify_password(request.old_password, user.password_hash or ""):
            raise ValidationException(message="原密码错误")
        if not self._check_email_code(user.id, request.code):
            raise ValidationException(message="邮箱验证码错误或已过期")
        user.password_hash = hash_password(request.new_password)
        self._user_repository.commit()
        # 发站内信（失败不阻断主流程）
        with suppress(Exception):
            if self._station_service is not None:
                self._station_service.send_station(
                    user_id=user.id,
                    title="密码已修改",
                    content=f"您的密码已于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 修改",
                )
        # 发邮件（失败不阻断主流程）
        with suppress(Exception):
            self._dispatch_email(
                event_type=NotificationEvent.USER_PASSWORD_CHANGED.value,
                email=user.email,
                variables={
                    "username": user.name or user.username,
                    "changed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                },
            )

    # ── 菜单树 ─────────────────────────────────────────────

    def get_my_menus(self, current_user: CurrentUser) -> list[dict[str, Any]]:
        """返回当前用户可见的菜单树。
        超管（权限含 "*"）可见全部启用菜单；普通用户仅可见
        关联权限码为空或命中自身权限的菜单，并过滤无可见子菜单的目录。

        Args:
            current_user: 当前登录用户

        Returns:
            list[dict[str, Any]]: 菜单树列表（目录/菜单嵌套结构）
        """
        all_menus = self._menu_repository.list_enabled()
        if "*" in current_user.permissions:
            visible = all_menus
        else:
            visible = [m for m in all_menus if not m.perm_code or m.perm_code in current_user.permissions]
        menu_map: dict[int, dict[str, Any]] = {
            m.id: {
                "id": m.id,
                "parent_id": m.parent_id,
                "title": m.title,
                "path": m.path,
                "icon": m.icon,
                "type": m.type,
                "children": [],
            }
            for m in visible
        }
        tree: list[dict[str, Any]] = []
        for menu in menu_map.values():
            if menu["parent_id"] == MENU_ROOT_PARENT_ID:
                tree.append(menu)
            elif menu["parent_id"] in menu_map:
                menu_map[menu["parent_id"]]["children"].append(menu)
        return self._prune_menu_tree(tree)

    @staticmethod
    def _prune_menu_tree(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """递归过滤没有可见子菜单的目录节点。

        Args:
            nodes: 待过滤的菜单节点列表

        Returns:
            list[dict[str, Any]]: 过滤后的菜单节点列表
        """
        result: list[dict[str, Any]] = []
        for node in nodes:
            node["children"] = ProfileService._prune_menu_tree(node["children"])
            if node["type"] == MENU_TYPE_DIRECTORY and not node["children"]:
                continue
            result.append(node)
        return result

    # ── 通知偏好 ───────────────────────────────────────────

    def get_notification_preferences(self, user_id: int) -> dict[str, Any]:
        """获取当前用户的完整通知偏好（含全部事件×渠道及默认值）。

        Args:
            user_id: 当前用户 ID

        Returns:
            dict[str, Any]: {"events": [{event, name, channels: [{code, name, enabled}]}]}
        """
        rows = self._preference_repository.list_by_user(user_id)
        prefs: dict[str, dict[str, bool]] = {}
        for row in rows:
            prefs.setdefault(row.event_type, {})[row.channel] = row.enabled
        events = []
        for event in NotificationEvent:
            channels = [
                {
                    "code": channel.mark,
                    "name": channel.desc,
                    # 默认站内信开
                    "enabled": prefs.get(event.mark, {}).get(channel.mark, channel.mark == DEFAULT_ENABLED_CHANNEL),
                }
                for channel in NotificationChannel
            ]
            events.append({"event": event.mark, "name": event.desc, "channels": channels})
        return {"events": events}

    def update_notification_preferences(self, user_id: int, prefs: dict[str, dict[str, bool]]) -> None:
        """按 用户 + 事件 + 渠道 唯一键 upsert 通知偏好。

        Args:
            user_id: 当前用户 ID
            prefs: {event_type: {channel: enabled}} 偏好结构
        """
        for event_type, channels in prefs.items():
            for channel, enabled in channels.items():
                row = self._preference_repository.get_by_user_event_channel(
                    user_id=user_id, event_type=event_type, channel=channel
                )
                if row:
                    row.enabled = enabled
                else:
                    self._preference_repository.create(
                        UserNotificationPreferenceEntity(
                            user_id=user_id,
                            event_type=event_type,
                            channel=channel,
                            enabled=enabled,
                        )
                    )
        self._preference_repository.commit()

    # ── 通知接收人 ─────────────────────────────────────────

    def get_recipients(self, user_id: int) -> dict[str, Any]:
        """获取当前用户的通知接收人列表。

        Args:
            user_id: 当前用户 ID

        Returns:
            dict[str, Any]: {"items": [{id, channel, recipient, label, enabled}]}
        """
        rows = self._recipient_repository.list_by_user(user_id)
        return {
            "items": [
                {
                    "id": r.id,
                    "channel": r.channel,
                    "recipient": r.recipient,
                    "label": r.label,
                    "enabled": r.enabled,
                }
                for r in rows
            ]
        }

    def add_recipient(self, user_id: int, request: NotificationRecipientCreateRequest) -> int:
        """新增当前用户的通知接收人。

        Args:
            user_id: 当前用户 ID
            request: 新增接收人入参

        Returns:
            int: 新建接收人的主键 ID
        """
        entity = self._recipient_repository.create(
            NotificationRecipientEntity(
                user_id=user_id,
                channel=request.channel,
                recipient=request.recipient,
                label=request.label,
                enabled=request.enabled,
            )
        )
        self._recipient_repository.commit()
        return entity.id

    def update_recipient(
        self,
        user_id: int,
        recipient_id: int,
        request: NotificationRecipientUpdateRequest,
    ) -> None:
        """更新当前用户的通知接收人（仅更新传入字段）。

        Args:
            user_id: 当前用户 ID
            recipient_id: 接收人主键 ID
            request: 更新接收人入参

        Raises:
            NotFoundException: 接收人不存在或不属于当前用户时抛出
        """
        row = self._recipient_repository.get_by_id_and_user(recipient_id, user_id)
        if row is None:
            raise NotFoundException(message="接收人不存在")
        patch = request.model_dump(exclude_unset=True)
        for key, value in patch.items():
            setattr(row, key, value)
        self._recipient_repository.commit()

    def delete_recipient(self, user_id: int, recipient_id: int) -> None:
        """删除当前用户的通知接收人。

        Args:
            user_id: 当前用户 ID
            recipient_id: 接收人主键 ID

        Raises:
            NotFoundException: 接收人不存在或不属于当前用户时抛出
        """
        row = self._recipient_repository.get_by_id_and_user(recipient_id, user_id)
        if row is None:
            raise NotFoundException(message="接收人不存在")
        self._recipient_repository.delete(recipient_id)
        self._recipient_repository.commit()

    # ── 安全设置：邮箱二次认证 ─────────────────────────────

    def send_verify_code(self, user_id: int) -> None:
        """向当前用户邮箱发送 6 位验证码（5 分钟有效）。

        Args:
            user_id: 当前用户 ID

        Raises:
            ValidationException: 账号未绑定邮箱时抛出
        """
        user = self._require_user(user_id)
        if not user.email:
            raise ValidationException(message="当前账号未绑定邮箱，无法发送验证码")
        code = f"{random.randint(VERIFY_CODE_MIN, VERIFY_CODE_MAX)}"
        self._cache.set(f"{VERIFY_CODE_CACHE_PREFIX}{user.id}", code, ttl=VERIFY_CODE_TTL_SECONDS)
        with suppress(Exception):
            self._dispatch_email(
                event_type=VERIFY_CODE_EVENT,
                email=user.email,
                variables={"code": code, "username": user.name or user.username},
            )

    def verify_and_update_phone(self, user_id: int, code: str, phone: str) -> None:
        """通过邮箱验证码校验后修改手机号。

        Args:
            user_id: 当前用户 ID
            code: 邮箱验证码（一次性）
            phone: 新手机号

        Raises:
            NotFoundException: 用户不存在时抛出
            ValidationException: 验证码错误或过期时抛出
        """
        user = self._require_user(user_id)
        if not self._check_email_code(user.id, code):
            raise ValidationException(message="邮箱验证码错误或已过期")
        user.phone = phone
        self._user_repository.commit()

    def verify_and_update_email(self, user_id: int, code: str, email: str) -> None:
        """通过原邮箱验证码校验后修改邮箱。

        Args:
            user_id: 当前用户 ID
            code: 原邮箱验证码（一次性）
            email: 新邮箱地址

        Raises:
            NotFoundException: 用户不存在时抛出
            ValidationException: 验证码错误或过期时抛出
        """
        user = self._require_user(user_id)
        if not self._check_email_code(user.id, code):
            raise ValidationException(message="原邮箱验证码错误或已过期")
        user.email = email
        self._user_repository.commit()

    # ── 内部工具 ───────────────────────────────────────────

    def _require_user(self, user_id: int) -> UserEntity:
        """按 ID 查询用户，不存在时抛出 NotFoundException。"""
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundException(message="用户不存在")
        return user

    def _check_email_code(self, user_id: int, code: str) -> bool:
        """校验邮箱验证码（一次性，校验通过后立即删除）。

        Args:
            user_id: 用户 ID
            code: 待校验的验证码

        Returns:
            bool: 校验是否通过
        """
        if not code:
            return False
        key = f"{VERIFY_CODE_CACHE_PREFIX}{user_id}"
        saved = self._cache.get(key)
        if saved != code:
            return False
        self._cache.delete(key)
        return True

    def _dispatch_email(self, event_type: str, email: str | None, variables: dict[str, Any]) -> None:
        """通过通知调度器发送邮件通知。

        Args:
            event_type: 通知事件类型（字符串编码）
            email: 接收邮箱（为空时静默跳过）
            variables: 模板变量
        """
        if self._dispatcher is None or not email:
            logger.debug(f"Email notification skipped: event={event_type} email={email}")
            return
        self._dispatcher.dispatch(
            event_type=event_type,
            recipients={"email": email},
            variables=variables,
        )
