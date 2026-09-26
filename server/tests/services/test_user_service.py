#!/usr/bin/env python3
"""
用户业务逻辑测试

测试用户 Service 在边界条件下的行为：
    - 创建：合法数据 / 重名 / 重邮箱
    - 更新：存在 / 不存在 / 部分字段
    - 删除：存在 / 不存在
    - 查询：分页
"""

from datetime import datetime

import pytest
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.user_entity import UserEntity
from src.schemas.user import UserCreateRequest
from src.services.user_service import UserService


class FakeUserRepository:
    """内存版 Repository 替身，用于单元测试 Service。"""

    def __init__(self) -> None:
        self._items: dict[int, UserEntity] = {}
        self._next_id: int = 1

    def _next(self) -> int:
        cid = self._next_id
        self._next_id += 1
        return cid

    def get_by_id(self, id: int) -> UserEntity | None:
        return self._items.get(id)

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
        entity.created_at = datetime.utcnow()
        entity.updated_at = entity.created_at
        self._items[entity.id] = entity
        return entity

    def update(self, id: int, entity: UserEntity) -> UserEntity | None:
        existing = self._items.get(id)
        if existing is None:
            return None
        for key in ("username", "email", "name", "age"):
            val = getattr(entity, key, None)
            if val not in (None, ""):
                setattr(existing, key, val)
        existing.updated_at = datetime.utcnow()
        return existing

    def delete(self, id: int) -> bool:
        return self._items.pop(id, None) is not None

    def count(self) -> int:
        return len(self._items)


class TestUserService:
    """UserService 单元测试。"""

    def setup_method(self) -> None:
        self.repo = FakeUserRepository()
        self.service = UserService(user_repository=self.repo)

    def test_create_user(self):
        """创建合法用户成功。"""
        data = UserCreateRequest(
            username="alice", email="alice@example.com", name="Alice", age=30
        )
        result = self.service.create(data.model_dump())
        assert result.id == 1
        assert result.username == "alice"

    def test_create_duplicate_username(self):
        """用户名冲突抛 ConflictException。"""
        first = UserCreateRequest(
            username="bob", email="bob1@example.com", name="Bob"
        )
        self.service.create(first.model_dump())

        dup = UserCreateRequest(
            username="bob", email="bob2@example.com", name="Bob2"
        )
        with pytest.raises(ConflictException):
            self.service.create(dup.model_dump())

    def test_update_existing_user(self):
        """更新存在的用户成功。"""
        created = self.service.create(
            UserCreateRequest(
                username="carol",
                email="carol@example.com",
                name="Carol",
            ).model_dump()
        )
        updated = self.service.update(created.id, {"name": "Carol Updated"})
        assert updated.name == "Carol Updated"
        assert updated.username == "carol"  # 未变更字段保持

    def test_update_missing_user_raises_not_found(self):
        """更新不存在的用户抛 NotFoundException。"""
        with pytest.raises(NotFoundException):
            self.service.update(999, {"name": "X"})

    def test_delete_existing_user(self):
        """删除存在的用户成功。"""
        created = self.service.create(
            UserCreateRequest(
                username="dave", email="dave@example.com", name="Dave"
            ).model_dump()
        )
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
                    username=f"user_{i}",
                    email=f"u{i}@example.com",
                    name=f"User {i}",
                ).model_dump()
            )

        page1 = self.service.get_all(page=1, page_size=2)
        assert len(page1["items"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        page3 = self.service.get_all(page=3, page_size=2)
        assert len(page3["items"]) == 1
