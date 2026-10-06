#!/usr/bin/env python3
"""个人中心业务逻辑。
个人中心（/api/admin/v1/profile）的业务规则与事务编排层：
    - 个人资料查询/修改、密码修改（验证码二次认证）
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
from src.constants.permissions import PermissionModule
from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger
from src.infras.cache import CacheProvider, get_cached_cache_provider
from src.models.entities.notification_config_entity import UserNotificationConfigEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.menu_repository import MenuRepository
from src.repositories.notification_config_repository import UserNotificationConfigRepository
from src.repositories.user_repository import UserRepository
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.profile import (
    ChangePasswordRequest,
    NotificationRecipientCreateRequest,
    NotificationRecipientUpdateRequest,
    UpdateMeRequest,
)
from src.services.admin.station_service import StationMessageService
from src.utils.security import hash_password, verify_password

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher


class ProfileService:
    """个人中心业务逻辑实现。"""

    def __init__(
        self,
        user_repository: UserRepository,
        menu_repository: MenuRepository,
        config_repository: UserNotificationConfigRepository,
        dispatcher: NotificationDispatcher | None = None,
        station_service: StationMessageService | None = None,
        cache: CacheProvider | None = None,
    ) -> None:
        """初始化个人中心服务。

        Args:
            user_repository: 用户数据访问仓库
            menu_repository: 菜单数据访问仓库
            config_repository: 用户通知配置仓库（事件×渠道开关 + 渠道级 recipient）
            dispatcher: 通知调度器（可选，未注入时邮件通知静默跳过）
            station_service: 站内信服务（可选，未注入时站内信静默跳过）
            cache: 缓存客户端（可选，未注入时使用全局缓存提供者）
        """
        self._user_repository = user_repository
        self._menu_repository = menu_repository
        self._config_repository = config_repository
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
        # 多角色体系下以下方实时查询的 roles 为准，避免响应字段冗余。
        data: dict[str, Any] = current_user.model_dump(exclude={"role_code"})
        roles = self._user_repository.get_roles_by_user_id(current_user.id)
        # 字段命名与用户列表接口的 roles 结构保持一致（role_name/role_code）
        data["roles"] = [
            {"id": r.id, "role_name": r.role_name, "role_code": r.role_code} for r in roles
        ]
        if "*" not in current_user.permissions:
            role_ids = [r.id for r in roles]
            perms = self._user_repository.get_permissions_by_role_ids(role_ids)
            data["permission_list"] = [
                {
                    "code": p.perm_code,
                    "name": p.perm_name,
                    "module": p.module,
                    "module_label": PermissionModule.get_desc_by_mark(p.module, p.module),
                }
                for p in perms
            ]
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
            # birthday 已在 schema 层规范化为 YYYY-MM-DD（含时区换算）
            setattr(user, key, value)
        self._user_repository.commit()

    def change_password(
        self,
        user_id: int,
        request: ChangePasswordRequest,
    ) -> None:
        """修改当前用户密码（需原密码 + 验证码二次认证）。
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
            raise ValidationException(message="验证码错误或已过期")
        user.password_hash = hash_password(request.new_password)
        self._user_repository.commit()
        # 改密后强制撤销全部已签发令牌（与开放平台门户域行为对齐）
        try:
            from src.infras.cache import get_cached_cache_provider
            provider = get_cached_cache_provider()
            provider.delete(f"login:{user_id}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"改密后清除 Redis 登录态失败: user_id={user_id} error={e}")
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

    # ── 通知偏好（事件 × 渠道）──────────────────────────────

    def get_notification_preferences(self, user_id: int) -> dict[str, Any]:
        """获取当前用户的完整通知偏好（事件 × 渠道开关，从 user_notification_configs 读取）。

        Args:
            user_id: 当前用户 ID

        Returns:
            dict[str, Any]: {"events": [{event, name, channels: [{code, name, enabled, recipient}]}]}
        """
        rows = self._config_repository.list_by_user_id(user_id)
        # 按 event 聚合已配置行
        configured: dict[str, dict[str, tuple[bool, str]]] = {}
        for row in rows:
            configured.setdefault(row.event_type, {})[row.channel] = (bool(row.enabled), row.recipient or "")
        events = []
        for event in NotificationEvent:
            channels = []
            for channel in NotificationChannel:
                cfg = configured.get(event.mark, {}).get(channel.mark)
                # 默认站内信开，其他渠道关；未配置行不展示 recipient
                default_enabled = channel.mark == DEFAULT_ENABLED_CHANNEL
                channels.append(
                    {
                        "code": channel.mark,
                        "name": channel.desc,
                        "enabled": cfg[0] if cfg else default_enabled,
                        "recipient": cfg[1] if cfg else "",
                    }
                )
            events.append({"event": event.mark, "name": event.desc, "channels": channels})
        return {"events": events}

    def update_notification_preferences(
        self, user_id: int, prefs: dict[str, dict[str, bool]]
    ) -> None:
        """按 (user, event, channel) 唯一键 upsert 通知开关。

        recipient 与事件无关：若该用户在某渠道下已有 recipient（如已配置 webhook），
        新写入的 event×channel 行继承该 recipient；station 渠道 recipient 恒为空串。

        Args:
            user_id: 当前用户 ID
            prefs: {event_type: {channel: enabled}} 偏好结构
        """
        # 缓存每个 channel 当前的 recipient，避免逐行查库
        existing_by_channel: dict[str, str] = {}
        for ch in NotificationChannel:
            rows = self._config_repository.list_by_user_and_channel(user_id, ch.mark)
            for r in rows:
                if r.recipient:
                    existing_by_channel[ch.mark] = r.recipient
                    break

        for event_type, channels in prefs.items():
            for channel, enabled in channels.items():
                row = self._config_repository.get_by_user_event_channel(
                    user_id=user_id, event_type=event_type, channel=channel
                )
                if row:
                    row.enabled = bool(enabled)
                else:
                    recipient = "" if channel == "station" else existing_by_channel.get(channel, "")
                    self._config_repository.create(
                        UserNotificationConfigEntity(
                            user_id=user_id,
                            event_type=event_type,
                            channel=channel,
                            recipient=recipient,
                            enabled=bool(enabled),
                        )
                    )
        self._config_repository.commit()

    # ── 通知接收人（渠道级 recipient，与事件无关）────────────

    def get_recipients(self, user_id: int) -> dict[str, Any]:
        """获取当前用户各渠道的接收方（按渠道聚合，每个渠道取一份 recipient）。

        Args:
            user_id: 当前用户 ID

        Returns:
            dict[str, Any]: {"items": [{channel, recipient, enabled}]}
        """
        rows = self._config_repository.list_by_user_id(user_id)
        # 按 channel 聚合：取该 channel 下任一非空 recipient
        channel_recipient: dict[str, str] = {}
        channel_enabled: dict[str, bool] = {}
        for row in rows:
            if row.channel == "station":
                continue
            if row.recipient and row.channel not in channel_recipient:
                channel_recipient[row.channel] = row.recipient
            channel_enabled.setdefault(row.channel, bool(row.enabled))
        items = [
            {
                "channel": channel,
                "recipient": recipient,
                "enabled": channel_enabled.get(channel, False),
            }
            for channel, recipient in channel_recipient.items()
        ]
        return {"items": items}

    def add_recipient(self, user_id: int, request: NotificationRecipientCreateRequest) -> None:
        """新增/更新当前用户某渠道的接收方（单值，同步刷新该渠道下所有事件行）。

        Args:
            user_id: 当前用户 ID
            request: 接收人入参（channel/recipient/enabled）
        """
        self._config_repository.upsert_channel_recipient(
            user_id=user_id,
            channel=request.channel,
            recipient=request.recipient,
            enabled=request.enabled,
        )
        self._config_repository.commit()

    def update_recipient(
        self,
        user_id: int,
        request: NotificationRecipientUpdateRequest,
    ) -> None:
        """更新当前用户某渠道的接收方（同 add_recipient，upsert 语义）。

        Args:
            user_id: 当前用户 ID
            request: 更新入参（channel/recipient/enabled）
        """
        recipient = request.recipient
        enabled = request.enabled if request.enabled is not None else True
        self._config_repository.upsert_channel_recipient(
            user_id=user_id,
            channel=request.channel,
            recipient=recipient or "",
            enabled=bool(enabled),
        )
        self._config_repository.commit()

    def delete_recipient(self, user_id: int, channel: str, recipient: str) -> None:
        """清空当前用户某渠道的接收方（所有事件行 recipient 置空并禁用该渠道）。

        Args:
            user_id: 当前用户 ID
            channel: 通知渠道
            recipient: 接收人地址（保留参数兼容旧调用，单值场景下不校验）
        """
        self._config_repository.upsert_channel_recipient(
            user_id=user_id,
            channel=channel,
            recipient="",
            enabled=False,
        )
        self._config_repository.commit()

    def test_recipient(self, user_id: int, channel: str) -> dict[str, Any]:
        """用当前用户在指定渠道配置的接收方发一条测试消息。

        仅支持 dingtalk / feishu（webhook 群机器人）。从 user_notification_configs
        读该用户在该 channel 下的 recipient，临时构造 provider 发测试消息，
        不经过系统级 registry（系统 registry 用的是管理员配置的 webhook）。

        Args:
            user_id: 当前用户 ID
            channel: 渠道标识（dingtalk / feishu）

        Returns:
            {"success": bool, "error": str | None}

        Raises:
            NotFoundException: 用户未配置该渠道接收方时抛出
        """
        if channel not in ("dingtalk", "feishu"):
            raise NotFoundException(message="仅支持测试钉钉/飞书 Webhook")
        rows = self._config_repository.list_by_user_and_channel(user_id, channel)
        recipient = next((r.recipient for r in rows if r.recipient), "")
        if not recipient:
            raise NotFoundException(message=f"尚未配置{channel} Webhook，请先填写并保存")

        from src.infras.notification import (
            BaseNotificationProvider,
            DingTalkNotificationProvider,
            FeishuNotificationProvider,
            NotificationMessage,
        )

        if channel == "dingtalk":
            provider: BaseNotificationProvider = DingTalkNotificationProvider(webhook_url=recipient)
        else:
            provider = FeishuNotificationProvider(webhook_url=recipient)

        try:
            ok = provider.send(
                NotificationMessage(
                    recipient=recipient,
                    subject="Webhook 连通性测试",
                    content="这是一条来自汉江管理系统的 Webhook 连通性测试消息。",
                )
            )
            return {"success": ok, "error": None if ok else "发送失败，请检查 Webhook 地址"}
        except Exception as exc:  # noqa: BLE001 - 测试失败统一收敛
            logger.warning("User webhook test failed user=%s channel=%s: %s", user_id, channel, exc)
            return {"success": False, "error": "发送失败，请检查 Webhook 地址"}

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
        try:
            self._dispatch_email(
                event_type=VERIFY_CODE_EVENT,
                email=user.email,
                variables={"code": code, "username": user.name or user.username},
            )
        except Exception as exc:  # noqa: BLE001 - 邮件发送失败不阻断接口，但必须记录
            logger.error("验证码邮件发送失败: user_id=%s error=%s", user.id, exc)

    def verify_and_update_phone(self, user_id: int, code: str, phone: str) -> None:
        """通过验证码校验后修改手机号。

        Args:
            user_id: 当前用户 ID
            code: 验证码（一次性）
            phone: 新手机号

        Raises:
            NotFoundException: 用户不存在时抛出
            ValidationException: 验证码错误或过期时抛出
        """
        user = self._require_user(user_id)
        if not self._check_email_code(user.id, code):
            raise ValidationException(message="验证码错误或已过期")
        user.phone = phone
        self._user_repository.commit()

    def verify_and_update_email(self, user_id: int, code: str, email: str) -> None:
        """通过原验证码校验后修改邮箱。

        Args:
            user_id: 当前用户 ID
            code: 原验证码（一次性）
            email: 新邮箱地址

        Raises:
            NotFoundException: 用户不存在时抛出
            ValidationException: 验证码错误或过期时抛出
        """
        user = self._require_user(user_id)
        if not self._check_email_code(user.id, code):
            raise ValidationException(message="原验证码错误或已过期")
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
        """校验验证码（一次性，校验通过后立即删除）。

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
