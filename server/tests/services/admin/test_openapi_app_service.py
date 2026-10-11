#!/usr/bin/env python3
"""管理端开放应用服务测试。

测试应用创建行为与通知派发：
    - 创建成功：派发 openapi_app.created 操作者回执（dispatcher）
    - admin 归属且归属人=操作者本人：owner 站内信跳过（自管自用）
    - developer 归属（管理员代建）：开发者收到门户站内信
    - 未注入 dispatcher：创建正常完成
"""

from datetime import UTC, datetime

from src.constants.enums import NotificationEvent
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.services.admin.openapi_app_service import OpenApiAppService


class FakeOpenApiAppRepository:
    """内存版应用仓库替身。"""

    session = None

    def __init__(self) -> None:
        self._items: dict[int, OpenApiAppEntity] = {}
        self._next_id = 1

    def get_by_app_id(self, app_id: str) -> OpenApiAppEntity | None:
        return next((e for e in self._items.values() if e.app_id == app_id), None)

    def create(self, entity: OpenApiAppEntity) -> OpenApiAppEntity:
        entity.id = self._next_id
        self._next_id += 1
        entity.created_at = datetime.now(UTC)
        self._items[entity.id] = entity
        return entity

    def get_owner_user(self, owner_id: int):
        return None

    def get_owner_developer(self, owner_id: int):
        return None


class FakeRegistrationRepository:
    """审批仓库替身。"""

    session = None


class FakeDispatcher:
    """记录 dispatch_for_user 调用的替身。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def dispatch_for_user(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeSession:
    """记录 add 的会话替身（捕获归属方站内信）。"""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def _make_service(dispatcher: FakeDispatcher | None = None) -> tuple[OpenApiAppService, FakeSession]:
    svc = OpenApiAppService(
        repo=FakeOpenApiAppRepository(),
        registration_repo=FakeRegistrationRepository(),
        dispatcher=dispatcher,
    )
    session = FakeSession()
    svc._repository.session = session
    return svc, session


def _create_kwargs(**overrides) -> dict:
    kwargs = {
        "name": "jian",
        "description": "测试应用",
        "scopes": ["user:read"],
        "rate_limit_per_minute": 60,
        "auth_mode": "hmac",
        "operator": {"operator_id": 5, "operator_name": "yangzhuang"},
    }
    kwargs.update(overrides)
    return kwargs


class TestCreateAppNotification:
    """应用创建通知派发行为。"""

    def test_create_dispatches_operator_receipt(self) -> None:
        """创建成功 → 派发 openapi_app.created 回执给操作者，携带应用名与 App ID。"""
        dispatcher = FakeDispatcher()
        svc, _ = _make_service(dispatcher)

        resp, app_key = svc.create_app(**_create_kwargs())
        assert app_key
        assert len(dispatcher.calls) == 1
        call = dispatcher.calls[0]
        assert call["user_id"] == 5
        assert call["event_type"] == NotificationEvent.OPENAPI_APP_CREATED
        assert call["variables"]["name"] == "jian"
        assert call["variables"]["app_id"] == resp.app_id

    def test_create_admin_owned_by_self_skips_owner_message(self) -> None:
        """admin 归属且归属人=操作者本人 → 不写 owner 站内信（自管自用）。"""
        dispatcher = FakeDispatcher()
        svc, session = _make_service(dispatcher)

        svc.create_app(**_create_kwargs(owner_type="admin", owner_id=5))
        assert session.added == []

    def test_create_developer_owned_sends_developer_message(self) -> None:
        """developer 归属（管理员代建）→ 开发者收到门户站内信。"""
        dispatcher = FakeDispatcher()
        svc, session = _make_service(dispatcher)

        svc.create_app(**_create_kwargs(owner_type="developer", owner_id=7))
        assert len(session.added) == 1
        assert isinstance(session.added[0], DeveloperMessageEntity)

    def test_create_without_dispatcher_still_succeeds(self) -> None:
        """未注入 dispatcher → 创建正常完成。"""
        svc, _ = _make_service(None)

        resp, app_key = svc.create_app(**_create_kwargs())
        assert resp.name == "jian"
        assert app_key
