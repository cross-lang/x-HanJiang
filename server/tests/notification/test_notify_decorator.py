#!/usr/bin/env python3
"""notify 装饰器测试 — 目标解析与多目标派发行为。"""

from typing import Any

from src.notification.decorators import notify


class FakeDispatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def dispatch_for_user(self, user_id: int, event_type: Any, variables: dict, source: str) -> None:
        self.calls.append({"user_id": user_id, "event_type": event_type, "variables": variables})


class FakeService:
    """被装饰方法的宿主，_dispatcher 为装饰器读取的派发入口。"""

    def __init__(self, dispatcher: FakeDispatcher) -> None:
        self._dispatcher = dispatcher

    @notify("user.created", target=("self", "operator"), vars_extractor=lambda r: {"username": r.username})
    def create(self, data: dict, operator: dict | None = None) -> Any:
        return type("R", (), {"id": data["new_id"], "username": data["username"]})()

    @notify("user.deleted", target="operator")
    def delete(self, id: int, operator: dict | None = None) -> bool:
        return True


class TestNotifyDecorator:
    def test_multi_target_dispatches_to_both(self) -> None:
        """多目标：被操作用户与操作者各派发一次。"""
        dispatcher = FakeDispatcher()
        service = FakeService(dispatcher)

        service.create({"new_id": 10, "username": "bob"}, operator={"operator_id": 5})

        assert [c["user_id"] for c in dispatcher.calls] == [10, 5]
        assert all(c["variables"] == {"username": "bob"} for c in dispatcher.calls)

    def test_same_user_deduplicated(self) -> None:
        """操作者即被操作用户（自己改自己）时只派发一次。"""
        dispatcher = FakeDispatcher()
        service = FakeService(dispatcher)

        service.create({"new_id": 5, "username": "self_op"}, operator={"operator_id": 5})

        assert [c["user_id"] for c in dispatcher.calls] == [5]

    def test_operator_target_resolves_operator_id(self) -> None:
        """target="operator"：从 kwargs.operator 取 operator_id。"""
        dispatcher = FakeDispatcher()
        service = FakeService(dispatcher)

        service.delete(10, operator={"operator_id": 5})

        assert [c["user_id"] for c in dispatcher.calls] == [5]

    def test_missing_operator_skips_dispatch(self) -> None:
        """操作者上下文缺失（operator_id 非法）时不派发、不报错。"""
        dispatcher = FakeDispatcher()
        service = FakeService(dispatcher)

        service.delete(10, operator={})
        service.delete(10)

        assert dispatcher.calls == []
