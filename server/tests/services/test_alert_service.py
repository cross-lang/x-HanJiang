#!/usr/bin/env python3
"""系统告警服务单元测试。

覆盖 src/services/alert_service.py：
    - send()：无会话（仅调用方接收人）/ 有会话（追加超管邮箱、超管短信、系统启用渠道，
      并做接收人去重）/ 超级管理员角色缺失
    - broadcast()：无会话直接跳过 / 遍历活跃用户逐个投递 / 单用户失败不影响整体计数

dispatcher 与数据访问组件均用内存 Fake 替身注入，不连真实 DB、不触网。
"""

from types import SimpleNamespace
from typing import Any

import src.services.alert_service as alert_module
from src.constants.enums import SystemRoleCode, UserStatus
from src.constants.notification import NotificationEvent, NotificationSource
from src.services.alert_service import AlertService, _dedup


class FakeDispatcher:
    """记录 dispatch / dispatch_for_user 调用的调度器替身。"""

    def __init__(self) -> None:
        self.dispatches: list[dict[str, Any]] = []
        self.user_dispatches: list[dict[str, Any]] = []

    def dispatch(self, **kwargs) -> list:
        self.dispatches.append(kwargs)
        return []

    def dispatch_for_user(self, **kwargs) -> list:
        self.user_dispatches.append(kwargs)
        return []


class FakeRoleRepo:
    """角色仓库替身：返回预置超管角色或 None。"""

    def __init__(self, role: SimpleNamespace | None) -> None:
        self._role = role

    def get_by_code(self, code: str) -> SimpleNamespace | None:
        return self._role


class FakeUserRepo:
    """用户仓库替身：按角色返回用户列表。"""

    def __init__(
        self, by_role: dict[int, list[Any]] | None = None, search_result: tuple[list, int] | None = None
    ) -> None:
        self._by_role = by_role or {}
        self._search_result = search_result or ([], 0)

    def get_by_role_id(self, role_id: int) -> list:
        return self._by_role.get(role_id, [])

    def search(self, keyword=None, status=None, skip=0, limit=100):
        return self._search_result


class FakeSysConfigRepo:
    """系统通知渠道配置替身：返回已启用渠道列表。"""

    def __init__(self, channels: list[SimpleNamespace] | None = None) -> None:
        self._channels = channels or []

    def list_all(self) -> list:
        return self._channels


def _user(user_id: int, email: str = "", phone: str = "", status: str = UserStatus.ENABLED.value) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, email=email, phone=phone, status=status)


def _cfg(channel: str, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(channel=channel, enabled=enabled)


class TestDedup:
    """接收人去重工具函数。"""

    def test_dedup_preserves_order_and_drops_empty(self) -> None:
        assert _dedup(["b", "a", "b", "", "a"]) == ["b", "a"]


class TestSend:
    """send() 指定接收人发送。"""

    def test_send_without_session_only_uses_caller_recipients(self) -> None:
        """无数据库会话：不追加超管/系统渠道，仅透传调用方接收人。"""
        dispatcher = FakeDispatcher()
        svc = AlertService(dispatcher=dispatcher, session=None)

        svc.send(subject="CPU 告警", message="CPU 90%", recipients={"email": ["oncall@example.com"]})

        call = dispatcher.dispatches[0]
        assert call["event_type"] == NotificationEvent.SYSTEM_ALERT
        assert call["source"] == NotificationSource.ALERT.value
        assert call["recipients"]["email"] == ["oncall@example.com"]
        # channels 来自默认路由（email/dingtalk/feishu），无 sms 追加
        assert "sms" not in call["channels"]
        assert call["variables"] == {"alert_title": "CPU 告警", "alert_message": "CPU 90%"}

    def test_send_appends_superadmin_and_system_channels(self) -> None:
        """有会话：追加超管邮箱/短信 + 系统启用渠道，并去重。"""
        dispatcher = FakeDispatcher()
        # 用 dummy 对象充当 session，真实查询全部由预置 fake repo 接管
        svc = AlertService(dispatcher=dispatcher, session=object())
        superadmin_role = SimpleNamespace(id=99)
        svc._role_repository = FakeRoleRepo(superadmin_role)
        svc._user_repository = FakeUserRepo(
            by_role={
                99: [
                    _user(1, email="root@example.com", phone="13900000001"),
                    _user(2, email="root@example.com", phone="13900000001"),  # 重复，应去重
                    _user(3, status=UserStatus.DISABLED.value, email="off@example.com"),  # 禁用，跳过
                ]
            }
        )
        svc._system_config_repository = FakeSysConfigRepo(
            [_cfg("dingtalk", enabled=True), _cfg("feishu", enabled=False)]  # 未启用不追加
        )

        svc.send(subject="磁盘满", message="/ 分区 99%", recipients={"email": ["caller@example.com"]})

        call = dispatcher.dispatches[0]
        merged = call["recipients"]
        # 调用方邮箱 + 超管邮箱去重合并
        assert merged["email"] == ["caller@example.com", "root@example.com"]
        # 超管短信渠道被加入
        assert merged["sms"] == ["13900000001"]
        assert "sms" in call["channels"]
        # 系统启用渠道 dingtalk 加入；feishu 未启用不加
        assert merged["dingtalk"] == ["dingtalk"]
        assert "dingtalk" in call["channels"]
        assert "feishu" not in merged

    def test_send_no_superadmin_role_skips_contacts(self) -> None:
        """超管角色不存在：不追加任何超管/系统渠道。"""
        dispatcher = FakeDispatcher()
        svc = AlertService(dispatcher=dispatcher, session=object())
        svc._role_repository = FakeRoleRepo(None)
        svc._user_repository = FakeUserRepo()
        svc._system_config_repository = FakeSysConfigRepo()

        svc.send(subject="x", message="y", recipients={"email": ["a@b.com"]})

        call = dispatcher.dispatches[0]
        assert call["recipients"] == {"email": ["a@b.com"]}
        assert "sms" not in call["channels"]


class TestBroadcast:
    """broadcast() 全体广播。"""

    def test_broadcast_without_session_returns_zero(self) -> None:
        """无会话：广播被跳过，返回 0。"""
        svc = AlertService(dispatcher=FakeDispatcher(), session=None)
        assert svc.broadcast("标题", "内容") == 0

    def test_broadcast_counts_success_and_tolerates_failure(self, monkeypatch) -> None:
        """遍历活跃用户逐个投递；单用户异常不中断，仅统计成功数。"""
        dispatcher = FakeDispatcher()

        def flaky_dispatch(**kwargs):
            # 模拟 3 号用户投递失败抛异常
            if kwargs["user_id"] == 3:
                raise RuntimeError("boom")
            return []

        dispatcher.dispatch_for_user = flaky_dispatch  # type: ignore[method-assign]

        svc = AlertService(dispatcher=dispatcher, session=object())
        monkeypatch.setattr(
            alert_module,
            "UserRepository",
            lambda session: FakeUserRepo(search_result=([_user(1), _user(2), _user(3)], 3)),
        )

        sent = svc.broadcast("维护通知", "今晚停机")
        assert sent == 2  # 3 号失败不计入，1/2 成功

    def test_broadcast_no_active_users(self, monkeypatch) -> None:
        """无活跃用户：成功数为 0。"""
        svc = AlertService(dispatcher=FakeDispatcher(), session=object())
        monkeypatch.setattr(alert_module, "UserRepository", lambda session: FakeUserRepo(search_result=([], 0)))
        assert svc.broadcast("标题", "内容") == 0


def test_superadmin_mark_import():
    """保证枚举引用有效（防止误改 mark）。"""
    assert SystemRoleCode.SUPERADMIN.mark == "superadmin"
