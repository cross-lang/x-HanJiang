#!/usr/bin/env python3
"""
个人中心通知模块测试

测试 ProfileService 通知偏好与渠道接收人在分表结构下的行为：
    - 渠道接收人：绑定落库 / 幂等更新 / 解绑 / 未配置时测试报错
    - 通知偏好矩阵：保存生成渠道配置行与订阅行 / email recipient 同步 / 退订删除订阅行
    - 调度读取：build_recipients_map 的 订阅存在 + 渠道启用 + recipient 非空 三重条件
"""

from types import SimpleNamespace

import pytest
from src.core.exceptions import NotFoundException
from src.models.entities.notification_config_entity import UserNotificationConfigEntity
from src.models.entities.user_entity import UserEntity
from src.models.entities.user_event_notification_entity import UserEventNotificationEntity
from src.schemas.admin.profile import NotificationRecipientCreateRequest, NotificationRecipientUpdateRequest
from src.services.admin.profile_service import ProfileService


class FakeUserNotificationConfigRepository:
    """内存版 Repository 替身：渠道配置表 + 事件订阅表，用于单元测试 Service。"""

    def __init__(self) -> None:
        self._config_by_key: dict[tuple[int, str], UserNotificationConfigEntity] = {}
        self._config_by_id: dict[int, UserNotificationConfigEntity] = {}
        self._subscriptions: set[tuple[int, str]] = set()
        self._next_id: int = 1
        self.commit_count: int = 0

    def _insert(self, user_id: int, channel: str) -> UserNotificationConfigEntity:
        config = UserNotificationConfigEntity(user_id=user_id, channel=channel, recipient="", enabled=True)
        config.id = self._next_id
        self._next_id += 1
        self._config_by_key[(user_id, channel)] = config
        self._config_by_id[config.id] = config
        return config

    def list_by_user_id(self, user_id: int) -> list[UserNotificationConfigEntity]:
        return [c for (uid, _), c in self._config_by_key.items() if uid == user_id]

    def get_by_user_channel(self, user_id: int, channel: str) -> UserNotificationConfigEntity | None:
        return self._config_by_key.get((user_id, channel))

    def get_or_create_channel_config(self, user_id: int, channel: str) -> UserNotificationConfigEntity:
        return self._config_by_key.get((user_id, channel)) or self._insert(user_id, channel)

    def list_subscriptions(self, user_id: int) -> list[UserEventNotificationEntity]:
        owned_ids = {c.id for c in self.list_by_user_id(user_id)}
        return [
            UserEventNotificationEntity(config_id=cid, event_type=etype)
            for cid, etype in self._subscriptions
            if cid in owned_ids
        ]

    def get_subscription(self, config_id: int, event_type: str) -> UserEventNotificationEntity | None:
        if (config_id, event_type) in self._subscriptions:
            return UserEventNotificationEntity(config_id=config_id, event_type=event_type)
        return None

    def subscribe(self, config_id: int, event_type: str) -> None:
        self._subscriptions.add((config_id, event_type))

    def unsubscribe(self, config_id: int, event_type: str) -> None:
        self._subscriptions.discard((config_id, event_type))

    def build_recipients_map(self, user_id: int, event_type: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for config in self.list_by_user_id(user_id):
            if not config.enabled or (config.id, event_type) not in self._subscriptions:
                continue
            if config.channel == "station":
                # 站内信接收方为收件箱协议地址
                result["station"] = f"user:{user_id}"
                continue
            if config.recipient:
                result[config.channel] = config.recipient
        return result

    def commit(self) -> None:
        self.commit_count += 1


class FakeUserRepository:
    """内存版用户仓库替身，仅提供 _require_user 所需接口。"""

    def __init__(self, user: UserEntity | None) -> None:
        self._user = user

    def get_by_id(self, id: int) -> UserEntity | None:
        return self._user


def _build_service(config_repo: FakeUserNotificationConfigRepository, user: UserEntity | None = None) -> ProfileService:
    return ProfileService(
        user_repository=FakeUserRepository(user),
        menu_repository=SimpleNamespace(),  # 通知相关路径不使用菜单仓库
        config_repository=config_repo,  # type: ignore[arg-type]
        dispatcher=None,
        station_service=None,
        cache=SimpleNamespace(set=lambda *args, **kwargs: None),
    )


def _make_user(user_id: int = 1, email: str = "alice@qq.com") -> UserEntity:
    return UserEntity(id=user_id, username="alice", name="Alice", email=email)


class TestChannelRecipient:
    """渠道接收人（第三方 Webhook 绑定）行为。"""

    def test_add_recipient_persists_for_fresh_user(self) -> None:
        """回归：全新用户（无任何配置行）绑定 Webhook 必须落库，不再静默丢失。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo)

        service.add_recipient(
            1,
            NotificationRecipientCreateRequest(
                channel="dingtalk", recipient="https://oapi.dingtalk.com/robot/send?access_token=x"
            ),
        )

        config = repo.get_by_user_channel(1, "dingtalk")
        assert config is not None
        assert config.recipient == "https://oapi.dingtalk.com/robot/send?access_token=x"
        assert config.enabled is True
        assert repo.commit_count == 1

    def test_add_recipient_idempotent_update(self) -> None:
        """重复保存即更新：仍是一行，recipient 覆盖为新值。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo)
        req1 = NotificationRecipientCreateRequest(channel="feishu", recipient="https://open.feishu.cn/a")
        req2 = NotificationRecipientCreateRequest(channel="feishu", recipient="https://open.feishu.cn/b")

        service.add_recipient(1, req1)
        service.add_recipient(1, req2)

        configs = [c for c in repo.list_by_user_id(1) if c.channel == "feishu"]
        assert len(configs) == 1
        assert configs[0].recipient == "https://open.feishu.cn/b"

    def test_update_recipient_keeps_subscriptions_untouched(self) -> None:
        """渠道接收人写入只动配置表，不影响事件订阅关系。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo)
        service.add_recipient(
            1, NotificationRecipientCreateRequest(channel="dingtalk", recipient="https://oapi.dingtalk.com/old")
        )
        config = repo.get_by_user_channel(1, "dingtalk")
        assert config is not None
        repo.subscribe(config.id, "user.disabled")

        service.update_recipient(
            1,
            NotificationRecipientUpdateRequest(channel="dingtalk", recipient="https://oapi.dingtalk.com/new"),
        )

        assert repo.get_subscription(config.id, "user.disabled") is not None
        assert config.recipient == "https://oapi.dingtalk.com/new"

    def test_delete_recipient_clears_and_disables(self) -> None:
        """解绑：recipient 置空 + 渠道禁用，订阅行保留。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo)
        service.add_recipient(
            1, NotificationRecipientCreateRequest(channel="dingtalk", recipient="https://oapi.dingtalk.com/x")
        )
        config = repo.get_by_user_channel(1, "dingtalk")
        assert config is not None
        repo.subscribe(config.id, "user.profile_updated")

        service.delete_recipient(1, "dingtalk", "")

        assert config.recipient == ""
        assert config.enabled is False
        assert repo.get_subscription(config.id, "user.profile_updated") is not None

    def test_delete_recipient_noop_when_never_bound(self) -> None:
        """从未绑定时解绑不报错、不建行。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo)

        service.delete_recipient(1, "dingtalk", "")

        assert repo.get_by_user_channel(1, "dingtalk") is None

    def test_test_recipient_raises_when_not_configured(self) -> None:
        """回归：未配置渠道时测试接口抛 NotFoundException（提示先填写并保存）。"""
        service = _build_service(FakeUserNotificationConfigRepository())

        with pytest.raises(NotFoundException, match="尚未配置dingtalk Webhook"):
            service.test_recipient(1, "dingtalk")

    def test_test_recipient_reads_channel_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """已配置渠道：从渠道配置行读取 recipient 并发送，返回 success。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo)
        service.add_recipient(
            1, NotificationRecipientCreateRequest(channel="feishu", recipient="https://open.feishu.cn/hook")
        )
        monkeypatch.setattr(
            "src.infras.notification.FeishuNotificationProvider.send", lambda self, message: True, raising=False
        )

        result = service.test_recipient(1, "feishu")

        assert result == {"success": True, "error": None}


class TestNotificationPreferences:
    """通知偏好矩阵（事件订阅）行为。"""

    def test_update_preferences_creates_configs_and_subscriptions(self) -> None:
        """保存矩阵：创建渠道配置行 + 订阅行；取消勾选仅删订阅行，不删配置行。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo, user=_make_user())
        prefs = {
            "user.disabled": {"station": True, "dingtalk": True},
            "user.profile_updated": {"station": True, "dingtalk": False},
        }

        service.update_notification_preferences(1, prefs)

        station = repo.get_by_user_channel(1, "station")
        dingtalk = repo.get_by_user_channel(1, "dingtalk")
        assert station is not None and dingtalk is not None
        assert dingtalk.recipient == ""
        assert repo.get_subscription(station.id, "user.disabled") is not None
        assert repo.get_subscription(station.id, "user.profile_updated") is not None
        # 勾选 dingtalk 的仅 status_changed 一行
        assert repo.get_subscription(dingtalk.id, "user.disabled") is not None
        assert repo.get_subscription(dingtalk.id, "user.profile_updated") is None

    def test_update_preferences_syncs_email_recipient(self) -> None:
        """email 渠道 recipient 每次保存同步为当前用户邮箱。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo, user=_make_user(email="new@qq.com"))

        service.update_notification_preferences(1, {"user.disabled": {"email": True}})

        email_config = repo.get_by_user_channel(1, "email")
        assert email_config is not None
        assert email_config.recipient == "new@qq.com"

    def test_get_preferences_defaults_for_fresh_user(self) -> None:
        """全新用户：矩阵按默认规则展示（站内信开、其他渠道关、无 recipient）。"""
        service = _build_service(FakeUserNotificationConfigRepository())

        data = service.get_notification_preferences(1)

        by_event = {e["event"]: {c["code"]: c for c in e["channels"]} for e in data["events"]}
        cell = by_event["user.password_changed"]
        assert cell["station"]["enabled"] is True
        assert cell["dingtalk"]["enabled"] is False
        assert cell["dingtalk"]["recipient"] == ""

    def test_get_preferences_reflects_subscriptions(self) -> None:
        """矩阵展示以订阅关系为准：订阅行存在即开，与渠道启用状态独立。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo, user=_make_user())
        service.update_notification_preferences(1, {"user.disabled": {"dingtalk": True}})

        data = service.get_notification_preferences(1)

        by_event = {e["event"]: {c["code"]: c for c in e["channels"]} for e in data["events"]}
        assert by_event["user.disabled"]["dingtalk"]["enabled"] is True
        assert by_event["user.profile_updated"]["dingtalk"]["enabled"] is False

    def test_get_recipients_lists_bound_channels_only(self) -> None:
        """接收人列表：仅返回已绑定（recipient 非空）的非站内信渠道。"""
        repo = FakeUserNotificationConfigRepository()
        service = _build_service(repo, user=_make_user())
        service.update_notification_preferences(1, {"user.disabled": {"email": True}})
        service.add_recipient(
            1, NotificationRecipientCreateRequest(channel="dingtalk", recipient="https://oapi.dingtalk.com/x")
        )

        data = service.get_recipients(1)

        channels = {item["channel"]: item for item in data["items"]}
        assert set(channels) == {"email", "dingtalk"}
        assert channels["dingtalk"]["recipient"] == "https://oapi.dingtalk.com/x"


class TestBuildRecipientsMap:
    """调度读取：三重生效条件。"""

    def _setup_bound(self, repo: FakeUserNotificationConfigRepository) -> UserNotificationConfigEntity:
        config = repo.get_or_create_channel_config(1, "dingtalk")
        config.recipient = "https://oapi.dingtalk.com/x"
        config.enabled = True
        return config

    def test_subscribed_enabled_with_recipient(self) -> None:
        repo = FakeUserNotificationConfigRepository()
        config = self._setup_bound(repo)
        repo.subscribe(config.id, "user.disabled")

        assert repo.build_recipients_map(1, "user.disabled") == {"dingtalk": "https://oapi.dingtalk.com/x"}

    def test_not_subscribed_excluded(self) -> None:
        repo = FakeUserNotificationConfigRepository()
        self._setup_bound(repo)  # 未订阅任何事件

        assert repo.build_recipients_map(1, "user.disabled") == {}

    def test_disabled_channel_excluded(self) -> None:
        repo = FakeUserNotificationConfigRepository()
        config = self._setup_bound(repo)
        repo.subscribe(config.id, "user.disabled")
        config.enabled = False

        assert repo.build_recipients_map(1, "user.disabled") == {}

    def test_empty_recipient_excluded(self) -> None:
        repo = FakeUserNotificationConfigRepository()
        config = self._setup_bound(repo)
        repo.subscribe(config.id, "user.disabled")
        config.recipient = ""

        assert repo.build_recipients_map(1, "user.disabled") == {}

    def test_station_subscription_maps_to_inbox_protocol(self) -> None:
        """站内信订阅：接收方映射为收件箱协议地址 user:{user_id}，无需配置 recipient。"""
        repo = FakeUserNotificationConfigRepository()
        config = repo.get_or_create_channel_config(1, "station")
        repo.subscribe(config.id, "user.status_changed")

        assert repo.build_recipients_map(1, "user.status_changed") == {"station": "user:1"}

    def test_station_disabled_config_excluded(self) -> None:
        """站内信渠道被禁用时不投递。"""
        repo = FakeUserNotificationConfigRepository()
        config = repo.get_or_create_channel_config(1, "station")
        repo.subscribe(config.id, "user.status_changed")
        config.enabled = False

        assert repo.build_recipients_map(1, "user.status_changed") == {}
