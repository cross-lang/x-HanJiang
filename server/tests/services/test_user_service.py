#!/usr/bin/env python3
"""
用户业务逻辑测试

测试用户 Service 在边界条件下的行为：
    - 创建：合法数据 / 重名 / 重邮箱
    - 更新：存在 / 不存在 / 部分字段
    - 删除：存在 / 不存在
    - 查询：分页
"""

from datetime import UTC, datetime

import pytest
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.user_entity import UserEntity
from src.schemas.user import UserCreateRequest
from src.services.user_service import UserService


class FakeUserRepository:
    """内存版 Repository 替身，用于单元测试 Service。

    与 UserRepository 公开接口保持一致，便于测试隔离（不连接真实数据库）。
    """

    def __init__(self) -> None:
        self._items: dict[int, UserEntity] = {}
        self._next_id: int = 1

    def _next(self) -> int:
        cid = self._next_id
        self._next_id += 1
        return cid

    def get_by_id(self, id: int) -> UserEntity | None:
        return self._items.get(id)

    def get_by_email(self, email: str) -> UserEntity | None:
        return next((e for e in self._items.values() if e.email == email), None)

    def get_by_username(self, username: str) -> UserEntity | None:
        return next((e for e in self._items.values() if e.username == username), None)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserEntity]:
        all_items = list(self._items.values())
        return all_items[skip : skip + limit]

    def create(self, entity: UserEntity) -> UserEntity:
        # 模拟唯一约束
        for e in self._items.values():
            if e.username == entity.username:
                raise ConflictException(message=f"Username '{entity.username}' exists")
            if e.email == entity.email:
                raise ConflictException(message=f"Email '{entity.email}' exists")

        entity.id = self._next()
        entity.created_at = datetime.now(UTC)
        entity.updated_at = entity.created_at
        self._items[entity.id] = entity
        return entity

    def update(self, id: int, entity: UserEntity) -> UserEntity | None:
        existing = self._items.get(id)
        if existing is None:
            return None
        for key in ("username", "email", "name"):
            val = getattr(entity, key, None)
            if val not in (None, ""):
                setattr(existing, key, val)
        existing.updated_at = datetime.now(UTC)
        return existing

    def delete(self, id: int) -> bool:
        return self._items.pop(id, None) is not None

    def count(self) -> int:
        return len(self._items)

    def get_roles_by_user_id(self, user_id: int) -> list:
        """测试桩：不维护角色数据，返回空列表。"""
        return []

    def replace_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        """测试桩：忽略角色绑定，保持无副作用。"""
        return None


class TestUserService:
    """UserService 单元测试。"""

    def setup_method(self) -> None:
        self.repo = FakeUserRepository()
        self.service = UserService(user_repository=self.repo)

    @staticmethod
    def _payload(
        username: str = "alice",
        email: str = "alice@example.com",
        name: str = "Alice",
        **overrides,
    ) -> dict:
        """构造符合创建必填约束的请求参数（name/phone/gender/birthday/password/role_ids）。"""
        payload = {
            "username": username,
            "email": email,
            "password": "ChangeMe@123",
            "name": name,
            "phone": "13800000000",
            "gender": "male",
            "birthday": "1990-01-01",
            "role_ids": [1],
        }
        payload.update(overrides)
        return payload

    def test_create_user(self):
        """创建合法用户成功。"""
        data = UserCreateRequest(**self._payload())
        result = self.service.create(data.model_dump())
        assert result.id == 1
        assert result.username == "alice"

    def test_create_duplicate_username(self):
        """用户名冲突抛 ConflictException。"""
        first = UserCreateRequest(**self._payload(username="bob", email="bob1@example.com", name="Bob"))
        self.service.create(first.model_dump())

        dup = UserCreateRequest(**self._payload(username="bob", email="bob2@example.com", name="Bob2"))
        with pytest.raises(ConflictException):
            self.service.create(dup.model_dump())

    def test_update_existing_user(self):
        """更新存在的用户成功。"""
        created = self.service.create(UserCreateRequest(**self._payload(username="carol", name="Carol")).model_dump())
        updated = self.service.update(created.id, {"name": "Carol Updated"})
        assert updated.name == "Carol Updated"
        assert updated.username == "carol"  # 未变更字段保持

    def test_update_missing_user_raises_not_found(self):
        """更新不存在的用户抛 NotFoundException。"""
        with pytest.raises(NotFoundException):
            self.service.update(999, {"name": "X"})

    def test_delete_existing_user(self):
        """删除存在的用户成功。"""
        created = self.service.create(UserCreateRequest(**self._payload(username="dave", name="Dave")).model_dump())
        assert self.service.delete(created.id) is True
        assert self.service.get_by_id(created.id) is None

    def test_delete_missing_user_raises_not_found(self):
        """删除不存在的用户抛 NotFoundException。"""
        with pytest.raises(NotFoundException):
            self.service.delete(999)

    def test_get_all_pagination(self):
        """分页查询正确返回元数据。"""
        for i in range(5):
            self.service.create(
                UserCreateRequest(
                    **self._payload(username=f"user_{i}", email=f"u{i}@example.com", name=f"User {i}")
                ).model_dump()
            )

        page1 = self.service.get_all(page=1, page_size=2)
        assert len(page1["items"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page3 = self.service.get_all(page=3, page_size=2)
        assert len(page3["items"]) == 1
