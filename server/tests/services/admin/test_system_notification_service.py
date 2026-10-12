#!/usr/bin/env python3
"""系统通知（广播）服务单元测试。

覆盖 src/services/admin/system_notification_service.py：
    - publish：全员广播 / 维护参数自动拼正文 / 幂等命中 / 多渠道强推 /
      定向角色（角色缺失 / 角色下无人）/ 定向用户为空 / 无活跃用户
    - withdraw：不存在 / 已撤回幂等 / 成功
    - republish：不存在 / 非已撤回态拒绝 / 按快照重发成功
    - 查询：列表 / 详情 / 投递明细

全部数据访问与外部派发用内存 Fake 替身，不连真实 DB、不触网；审计由 conftest 降级。
"""

from types import SimpleNamespace
from typing import Any

import pytest
from src.constants.notification import (
    NotificationTargetType,
    SystemNotificationStatus,
    SystemNotificationType,
)
from src.core.exceptions import NotFoundException, ValidationException
from src.models.entities.system_notification_entity import SystemNotificationEntity
from src.services.admin.system_notification_service import SystemNotificationService

# ── 各类 Fake ─────────────────────────────────────────


class FakeNoticeRepository:
    """内存版系统通知仓库替身。"""

    def __init__(self) -> None:
        self._items: dict[int, SystemNotificationEntity] = {}
        self._next_id = 1
        self.commits = 0

    def create(self, entity: SystemNotificationEntity) -> SystemNotificationEntity:
        entity.id = self._next_id
        self._next_id += 1
        self._items[entity.id] = entity
        return entity

    def get_by_id(self, notice_id: int) -> SystemNotificationEntity | None:
        return self._items.get(notice_id)

    def get_by_client_request_id(self, client_request_id: str) -> SystemNotificationEntity | None:
        return next((e for e in self._items.values() if e.client_request_id == client_request_id), None)

    def search(self, notice_type=None, status=None, keyword=None, skip=0, limit=20):
        rows = list(self._items.values())
        return rows[skip : skip + limit], len(rows)

    def commit(self) -> None:
        self.commits += 1


class FakeUserRepository:
    """用户仓库替身。"""

    def __init__(self, users: list | None = None) -> None:
        self._users = users or []

    def get_by_role_id(self, role_id: int) -> list:
        return [u for u in self._users if getattr(u, "role_id", None) == role_id]

    def get_by_ids(self, user_ids: list[int]) -> list:
        return [u for u in self._users if u.id in set(user_ids)]

    def search(self, keyword=None, status=None, skip=0, limit=100):
        return list(self._users), len(self._users)


class FakeRoleRepository:
    """角色仓库替身：code → 角色。"""

    def __init__(self, roles: dict[str, SimpleNamespace] | None = None) -> None:
        self._roles = roles or {}

    def get_by_code(self, code: str) -> SimpleNamespace | None:
        return self._roles.get(code)


class FakeStationService:
    """站内信服务替身：记录批量广播调用。"""

    def __init__(self) -> None:
        self.batch_calls: list[dict[str, Any]] = []

    def send_station_batch(self, user_ids, title, content, *, source, event_type, operator_id=None) -> None:
        self.batch_calls.append(
            {"user_ids": list(user_ids), "title": title, "content": content, "source": source, "event_type": event_type}
        )


class FakeDispatcher:
    """调度器替身：记录强推调用，可配置失败。"""

    def __init__(self, fail_user_ids: set[int] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail = fail_user_ids or set()

    def dispatch_for_user(self, **kwargs) -> list:
        self.calls.append(kwargs)
        if kwargs["user_id"] in self._fail:
            raise RuntimeError("dispatch failed")
        return []


class FakeDeliveryRepository:
    """投递明细仓库替身。"""

    def __init__(self) -> None:
        self.rows: list[Any] = []

    def list_by_notification(self, notification_id, channel=None, status=None, skip=0, limit=20):
        return self.rows, len(self.rows)

    def count_by_notification_status(self, notification_id) -> dict[str, int]:
        return {"success": len(self.rows)}


def _user(user_id: int, role_id: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, role_id=role_id)


def _make_service(
    users=None, roles=None, fail_users=None
) -> tuple[SystemNotificationService, FakeNoticeRepository, FakeStationService, FakeDispatcher, FakeDeliveryRepository]:
    notice_repo = FakeNoticeRepository()
    user_repo = FakeUserRepository(users or [])
    role_repo = FakeRoleRepository(roles or {})
    station = FakeStationService()
    dispatcher = FakeDispatcher(fail_users)
    delivery_repo = FakeDeliveryRepository()
    svc = SystemNotificationService(
        notice_repository=notice_repo,
        user_repository=user_repo,
        role_repository=role_repo,
        station_service=station,
        dispatcher=dispatcher,
        delivery_repository=delivery_repo,
    )
    return svc, notice_repo, station, dispatcher, delivery_repo


# ── 发布 ───────────────────────────────────────────────


def _publish_one(svc) -> int:
    """通过 svc 发布一条普通通知，返回其 ID。"""
    entity, _, _ = svc.publish(title="t", content="c", notice_type=SystemNotificationType.NOTICE)
    return entity.id


class TestPublish:
    """发布系统通知行为。"""

    def test_publish_all_users_broadcasts_station(self) -> None:
        """全员发布：写通知记录并向所有活跃用户广播站内信。"""
        svc, notice_repo, station, dispatcher, _ = _make_service(users=[_user(1), _user(2)])

        entity, sent_count, idempotent = svc.publish(
            title="升级通知",
            content="今晚升级",
            notice_type=SystemNotificationType.NOTICE,
            operator={"operator_id": 1, "operator_name": "admin"},
        )

        assert idempotent is False
        assert sent_count == 0  # 未指定强推渠道
        assert entity.status == SystemNotificationStatus.PUBLISHED.value
        assert station.batch_calls[0]["user_ids"] == [1, 2]
        assert dispatcher.calls == []  # 未强推
        assert notice_repo.commits >= 1

    def test_publish_maintenance_auto_builds_content(self) -> None:
        """content 为空 + 维护参数 → 正文自动拼接，维护参数写入 metadata。"""
        svc, _, _, _, _ = _make_service(users=[_user(1)])

        entity, _, _ = svc.publish(
            title="维护",
            content=None,
            notice_type=SystemNotificationType.MAINTENANCE,
            maintenance_time="2026-10-13 22:00:00",
            duration_hours=2,
            reason="内核升级",
        )

        assert "系统将于" in entity.content
        assert "内核升级" in entity.content
        assert entity.metadata_json["maintenance_time"] == "2026-10-13 22:00:00"

    def test_publish_idempotent_hit(self) -> None:
        """同一 client_request_id 重复提交 → 直接返回首次结果，不重复广播。"""
        svc, _, station, _, _ = _make_service(users=[_user(1)])
        # 首次发布
        first, _, _ = svc.publish(
            title="t", content="c", notice_type=SystemNotificationType.NOTICE, client_request_id="req-key-12345"
        )
        station.batch_calls.clear()

        # 重复提交
        again, sent_count, idempotent = svc.publish(
            title="t", content="c", notice_type=SystemNotificationType.NOTICE, client_request_id="req-key-12345"
        )

        assert idempotent is True
        assert again.id == first.id
        assert station.batch_calls == []  # 未重复广播
        assert sent_count == 0

    def test_publish_with_push_channels_counts_success(self) -> None:
        """指定强推渠道 → 逐用户强推，成功计数；单用户失败不影响。"""
        svc, _, _, dispatcher, _ = _make_service(users=[_user(1), _user(2), _user(3)], fail_users={3})

        _, sent_count, _ = svc.publish(
            title="强推",
            content="正文",
            notice_type=SystemNotificationType.NOTICE,
            push_channels=["email", "feishu"],
        )

        assert sent_count == 2  # 3 号失败
        assert len(dispatcher.calls) == 3
        assert dispatcher.calls[0]["channels"] == ["email", "feishu"]
        assert dispatcher.calls[0]["pre_rendered"] == ("强推", "正文")

    def test_publish_roles_target_role_missing_raises(self) -> None:
        """按角色定向但角色不存在 → ValidationException。"""
        svc, _, _, _, _ = _make_service(users=[_user(1, role_id=9)])
        with pytest.raises(ValidationException):
            svc.publish(
                title="t",
                content="c",
                notice_type=SystemNotificationType.NOTICE,
                target_type=NotificationTargetType.ROLES,
                target_roles=["ghost"],
            )

    def test_publish_roles_no_users_raises(self) -> None:
        """角色存在但名下无用户 → ValidationException。"""
        svc, _, _, _, _ = _make_service(
            users=[],
            roles={"admin": SimpleNamespace(id=9)},
        )
        with pytest.raises(ValidationException):
            svc.publish(
                title="t",
                content="c",
                notice_type=SystemNotificationType.NOTICE,
                target_type=NotificationTargetType.ROLES,
                target_roles=["admin"],
            )

    def test_publish_users_target_empty_raises(self) -> None:
        """按用户定向但查无此人 → ValidationException。"""
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        with pytest.raises(ValidationException):
            svc.publish(
                title="t",
                content="c",
                notice_type=SystemNotificationType.NOTICE,
                target_type=NotificationTargetType.USERS,
                target_user_ids=[999],
            )

    def test_publish_no_active_users_raises(self) -> None:
        """全员定向但无活跃用户 → ValidationException。"""
        svc, _, _, _, _ = _make_service(users=[])
        with pytest.raises(ValidationException):
            svc.publish(title="t", content="c", notice_type=SystemNotificationType.NOTICE)


# ── 撤回 / 重新发布 ────────────────────────────────────


class TestWithdrawAndRepublish:
    """撤回与重新发布行为。"""

    def test_withdraw_not_found_raises(self) -> None:
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        with pytest.raises(NotFoundException):
            svc.withdraw(999)

    def test_withdraw_success_and_idempotent(self) -> None:
        svc, notice_repo, _, _, _ = _make_service(users=[_user(1)])
        notice_id = _publish_one(svc)

        svc.withdraw(notice_id)
        assert notice_repo.get_by_id(notice_id).status == SystemNotificationStatus.WITHDRAWN.value
        # 已撤回再撤回 → 幂等返回不报错
        svc.withdraw(notice_id)

    def test_republish_not_found_raises(self) -> None:
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        with pytest.raises(NotFoundException):
            svc.republish(999)

    def test_republish_non_withdrawn_raises(self) -> None:
        """未撤回的通知不可重新发布 → ValidationException。"""
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        notice_id = _publish_one(svc)
        with pytest.raises(ValidationException):
            svc.republish(notice_id)

    def test_republish_success(self) -> None:
        """撤回后按快照重新发布 → 状态回到已发布并再次广播。"""
        svc, notice_repo, station, _, _ = _make_service(users=[_user(1), _user(2)])
        notice_id = _publish_one(svc)
        svc.withdraw(notice_id)
        station.batch_calls.clear()

        entity, sent_count = svc.republish(notice_id)
        assert entity.status == SystemNotificationStatus.PUBLISHED.value
        assert entity.withdrawn_at is None
        assert station.batch_calls[0]["user_ids"] == [1, 2]
        assert sent_count == 0


# ── 查询 ─────────────────────────────────────────────


class TestQuery:
    """系统通知查询。"""

    def test_list_notices(self) -> None:
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        _publish_one(svc)
        _publish_one(svc)
        result = svc.list_notices(page=1, page_size=10)
        assert result.total == 2
        assert len(result.items) == 2

    def test_get_notice_found_and_missing(self) -> None:
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        notice_id = _publish_one(svc)
        assert svc.get_notice(notice_id).id == notice_id
        with pytest.raises(NotFoundException):
            svc.get_notice(999)

    def test_get_deliveries_not_found(self) -> None:
        svc, _, _, _, _ = _make_service(users=[_user(1)])
        with pytest.raises(NotFoundException):
            svc.get_deliveries(999)

    def test_get_deliveries_success(self) -> None:
        svc, _, _, _, delivery_repo = _make_service(users=[_user(1)])
        notice_id = _publish_one(svc)
        result = svc.get_deliveries(notice_id)
        assert result.total == 0
        assert result.stats == {"success": 0}
