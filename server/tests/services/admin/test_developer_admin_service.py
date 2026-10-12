#!/usr/bin/env python3
"""管理端开发者服务测试。

测试开发者启停/删除行为与通知派发：
    - 启停成功：派发 developer.enabled / developer.disabled 操作者回执
    - 删除成功：派发 developer.deleted 操作者回执
    - 同状态幂等：不派发
    - 开发者门户站内信随启停/删除写入
"""

from datetime import UTC, datetime

import pytest
from src.constants.notification import NotificationEvent
from src.core.exceptions import NotFoundException
from src.models.entities.developer_entity import DeveloperEntity
from src.services.admin.developer_admin_service import DeveloperService


class FakeDeveloperRepository:
    """内存版开发者仓库替身（session 属性供基类能力使用）。"""

    session = None

    def __init__(self) -> None:
        self._items: dict[int, DeveloperEntity] = {}

    def add_developer(self, e: DeveloperEntity) -> DeveloperEntity:
        self._items[e.id] = e
        return e

    def get_by_id(self, id: int) -> DeveloperEntity | None:
        return self._items.get(id)

    def flush(self) -> None: ...


class FakeOpenApiAppService:
    """应用服务替身：记录级联调用。"""

    def __init__(self) -> None:
        self.disabled: list[int] = []
        self.deleted: list[int] = []

    def disable_apps_by_owner(self, owner_type: str, owner_id: int) -> None:
        self.disabled.append(owner_id)

    def soft_delete_apps_by_owner(self, owner_type: str, owner_id: int) -> None:
        self.deleted.append(owner_id)


class FakeDispatcher:
    """记录 dispatch_for_user 调用的替身。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def dispatch_for_user(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeSession:
    """记录 add 的会话替身（捕获开发者门户站内信）。"""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def _make_developer(dev_id: int = 7, status: str = "enabled") -> DeveloperEntity:
    return DeveloperEntity(
        id=dev_id,
        username=f"dev{dev_id}",
        email=f"dev{dev_id}@example.com",
        password_hash="x",
        name="开发者",
        phone="",
        certification_status="none",
        status=status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_service(repo: FakeDeveloperRepository, dispatcher: FakeDispatcher | None = None) -> DeveloperService:
    svc = DeveloperService(
        repository=repo,
        openapi_app_service=FakeOpenApiAppService(),
        dispatcher=dispatcher,
    )
    svc._repository.session = FakeSession()
    return svc


class TestUpdateStatusNotification:
    """开发者启停通知派发行为。"""

    def test_disable_dispatches_operator_receipt(self) -> None:
        """禁用成功 → 派发 developer.disabled 给操作者。"""
        repo = FakeDeveloperRepository()
        repo.add_developer(_make_developer(status="enabled"))
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        service.update_status(7, "disabled", operator={"operator_id": 1})
        assert len(dispatcher.calls) == 1
        call = dispatcher.calls[0]
        assert call["user_id"] == 1
        assert call["event_type"] == NotificationEvent.DEVELOPER_DISABLED
        assert call["variables"] == {"developer_username": "dev7"}
        assert service._openapi_app_service.disabled == [7]

    def test_enable_dispatches_operator_receipt(self) -> None:
        """启用成功 → 派发 developer.enabled 给操作者。"""
        repo = FakeDeveloperRepository()
        repo.add_developer(_make_developer(status="disabled"))
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        service.update_status(7, "enabled", operator={"operator_id": 1})
        assert dispatcher.calls[0]["event_type"] == NotificationEvent.DEVELOPER_ENABLED

    def test_same_status_idempotent_no_dispatch(self) -> None:
        """同状态幂等返回，不派发。"""
        repo = FakeDeveloperRepository()
        repo.add_developer(_make_developer(status="enabled"))
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        service.update_status(7, "enabled", operator={"operator_id": 1})
        assert dispatcher.calls == []

    def test_missing_developer_raises_not_found(self) -> None:
        """开发者不存在 → NotFoundException。"""
        dispatcher = FakeDispatcher()
        service = _make_service(FakeDeveloperRepository(), dispatcher)

        with pytest.raises(NotFoundException):
            service.update_status(999, "disabled", operator={"operator_id": 1})
        assert dispatcher.calls == []


class TestDeleteNotification:
    """开发者删除通知派发行为。"""

    def test_delete_dispatches_operator_receipt_and_developer_message(self) -> None:
        """删除成功 → 派发 developer.deleted 回执 + 开发者门户站内信 + 级联删应用。"""
        repo = FakeDeveloperRepository()
        repo.add_developer(_make_developer())
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        assert service.delete(7, operator={"operator_id": 1}) is True
        assert dispatcher.calls[0]["event_type"] == NotificationEvent.DEVELOPER_DELETED
        assert service._openapi_app_service.deleted == [7]
        added = service._repository.session.added
        assert len(added) == 1  # 开发者门户站内信
