#!/usr/bin/env python3
"""角色业务逻辑测试。

测试角色 Service 的删除行为与通知派发：
    - 删除成功：派发 role.deleted 操作者回执
    - 有关联用户：拒绝删除（ConflictException），不派发
    - 角色不存在：NotFoundException
"""

import pytest
from src.constants.notification import NotificationEvent
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.user_entity import RoleEntity
from src.services.role_service import RoleService


class FakeRoleRepository:
    """内存版角色仓库替身（session 属性供关联仓库构造使用）。"""

    session = None

    def __init__(self) -> None:
        self._items: dict[int, RoleEntity] = {}

    def add_role(self, role: RoleEntity) -> RoleEntity:
        self._items[role.id] = role
        return role

    def get_by_id(self, id: int) -> RoleEntity | None:
        return self._items.get(id)

    def count_user_links(self, id: int) -> int:
        return self._user_links.get(id, 0)

    _user_links: dict[int, int] = {}

    def delete(self, id: int) -> bool:
        return self._items.pop(id, None) is not None


class FakeDispatcher:
    """记录 dispatch_for_user 调用的替身。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def dispatch_for_user(self, **kwargs) -> None:
        self.calls.append(kwargs)


def _make_role(role_id: int = 10, name: str = "运营") -> RoleEntity:
    return RoleEntity(
        id=role_id,
        role_name=name,
        role_code=f"code_{role_id}",
        description="",
        role_type="custom",
        status="enabled",
    )


def _make_service(repo: FakeRoleRepository, dispatcher: FakeDispatcher | None = None) -> RoleService:
    return RoleService(role_repository=repo, dispatcher=dispatcher)


class TestDeleteNotification:
    """角色删除通知派发行为。"""

    def test_delete_success_dispatches_operator_receipt(self) -> None:
        """删除成功 → 派发 role.deleted 给操作者，携带角色名。"""
        repo = FakeRoleRepository()
        repo.add_role(_make_role())
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        assert service.delete(10, operator={"operator_id": 1, "operator_name": "yangzhuang"}) is True
        assert len(dispatcher.calls) == 1
        call = dispatcher.calls[0]
        assert call["user_id"] == 1
        assert call["event_type"] == NotificationEvent.ROLE_DELETED
        assert call["variables"] == {"role_name": "运营"}

    def test_delete_with_user_links_rejected_no_dispatch(self) -> None:
        """角色有关联用户 → 冲突异常，不派发任何通知。"""
        repo = FakeRoleRepository()
        repo.add_role(_make_role())
        repo._user_links = {10: 3}
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        with pytest.raises(ConflictException):
            service.delete(10, operator={"operator_id": 1})
        assert dispatcher.calls == []

    def test_delete_missing_role_no_dispatch(self) -> None:
        """角色不存在 → NotFoundException，不派发。"""
        dispatcher = FakeDispatcher()
        service = _make_service(FakeRoleRepository(), dispatcher)

        with pytest.raises(NotFoundException):
            service.delete(999, operator={"operator_id": 1})
        assert dispatcher.calls == []

    def test_delete_without_operator_no_dispatch(self) -> None:
        """operator 缺失 operator_id → 跳过派发，删除本身成功。"""
        repo = FakeRoleRepository()
        repo.add_role(_make_role())
        dispatcher = FakeDispatcher()
        service = _make_service(repo, dispatcher)

        assert service.delete(10, operator=None) is True
        assert dispatcher.calls == []

    def test_delete_without_dispatcher_still_succeeds(self) -> None:
        """未注入 dispatcher（如单测环境）→ 删除正常完成。"""
        repo = FakeRoleRepository()
        repo.add_role(_make_role())
        service = _make_service(repo, None)

        assert service.delete(10, operator={"operator_id": 1}) is True
        assert repo.get_by_id(10) is None
