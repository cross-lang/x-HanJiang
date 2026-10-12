#!/usr/bin/env python3
"""用户仓储（UserRepository）单元测试。

用内存 SQLite 执行真实 SQLAlchemy 查询，覆盖：
    - 按用户名/邮箱/手机号查询
    - 按角色查用户、按 ID 批量查、按用户查角色
    - 权限码/权限实体查询（含已废弃过滤）
    - 用户角色整体替换、关键字/状态搜索分页
    - 软删除、更新最后登录
"""

from datetime import datetime

from sqlalchemy.orm import Session
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
    UserEntity,
    UserRoleEntity,
)
from src.repositories.user_repository import UserRepository


def _make_user(user_id: int, username: str, email: str, phone: str = "") -> UserEntity:
    return UserEntity(
        id=user_id,
        username=username,
        email=email,
        name=username,
        password_hash="x",
        phone=phone,
        status="enabled",
    )


class TestUserQueries:
    """单实体查询通道。"""

    def test_get_by_username(self, db_session: Session) -> None:
        db_session.add(_make_user(1, "alice", "alice@example.com"))
        db_session.flush()
        repo = UserRepository(session=db_session)
        assert repo.get_by_username("alice").id == 1
        assert repo.get_by_username("nobody") is None

    def test_get_by_email(self, db_session: Session) -> None:
        db_session.add(_make_user(1, "alice", "alice@example.com"))
        db_session.flush()
        repo = UserRepository(session=db_session)
        assert repo.get_by_email("alice@example.com").username == "alice"

    def test_get_by_phone(self, db_session: Session) -> None:
        db_session.add(_make_user(1, "alice", "alice@example.com", phone="13800000001"))
        db_session.flush()
        repo = UserRepository(session=db_session)
        assert repo.get_by_phone("13800000001").username == "alice"


class TestUserRelationQueries:
    """关联查询（用户-角色-权限多对多）。"""

    def _seed_graph(self, db_session: Session) -> None:
        """用户1 绑定角色10（权限 [100]），用户2 绑定角色20（权限 [200,201]）。"""
        db_session.add(_make_user(1, "alice", "a@example.com"))
        db_session.add(_make_user(2, "bob", "b@example.com"))
        db_session.add(RoleEntity(id=10, role_name="R1", role_code="admin", description=""))
        db_session.add(RoleEntity(id=20, role_name="R2", role_code="user", description=""))
        db_session.add(UserRoleEntity(user_id=1, role_id=10))
        db_session.add(UserRoleEntity(user_id=2, role_id=20))
        db_session.add(PermissionEntity(id=100, perm_code="a:view", perm_name="A", module="a", operation="view"))
        db_session.add(PermissionEntity(id=200, perm_code="b:view", perm_name="B", module="b", operation="view"))
        db_session.add(
            PermissionEntity(
                id=201, perm_code="b:admin", perm_name="B2", module="b", operation="edit", is_deprecated=True
            )
        )
        db_session.add(RolePermissionEntity(role_id=10, permission_id=100))
        db_session.add(RolePermissionEntity(role_id=20, permission_id=200))
        db_session.add(RolePermissionEntity(role_id=20, permission_id=201))
        db_session.flush()

    def test_get_by_role_id(self, db_session: Session) -> None:
        self._seed_graph(db_session)
        repo = UserRepository(session=db_session)
        users = repo.get_by_role_id(10)
        assert [u.username for u in users] == ["alice"]

    def test_get_by_ids(self, db_session: Session) -> None:
        self._seed_graph(db_session)
        repo = UserRepository(session=db_session)
        assert repo.get_by_ids([]) == []
        got = repo.get_by_ids([1, 2, 999])
        assert {u.id for u in got} == {1, 2}

    def test_get_roles_by_user_id(self, db_session: Session) -> None:
        self._seed_graph(db_session)
        repo = UserRepository(session=db_session)
        roles = repo.get_roles_by_user_id(1)
        assert [r.role_code for r in roles] == ["admin"]

    def test_get_perm_codes_by_role_ids(self, db_session: Session) -> None:
        self._seed_graph(db_session)
        repo = UserRepository(session=db_session)
        assert repo.get_perm_codes_by_role_ids([]) == []
        codes = repo.get_perm_codes_by_role_ids([10, 20])
        assert set(codes) == {"a:view", "b:view", "b:admin"}

    def test_get_permissions_by_role_ids_excludes_deprecated(self, db_session: Session) -> None:
        """仅返回未废弃权限，并按 sort_order 排序。"""
        self._seed_graph(db_session)
        repo = UserRepository(session=db_session)
        perms = repo.get_permissions_by_role_ids([20])
        # 201 已废弃，应被过滤
        assert [p.perm_code for p in perms] == ["b:view"]

    def test_replace_user_roles(self, db_session: Session) -> None:
        self._seed_graph(db_session)
        repo = UserRepository(session=db_session)
        repo.replace_user_roles(1, [20])
        db_session.flush()
        # 用户1 的角色关系被整体替换为 [20]
        roles = repo.get_roles_by_user_id(1)
        assert [r.id for r in roles] == [20]


class TestUserSearchAndDelete:
    """搜索分页、软删除、更新最后登录。"""

    def _seed_multi(self, db_session: Session) -> None:
        for i in range(3):
            db_session.add(
                UserEntity(
                    id=i + 1,
                    username=f"user{i}",
                    email=f"user{i}@example.com",
                    name=f"用户{i}",
                    password_hash="x",
                    status="enabled" if i != 2 else "disabled",
                )
            )
        db_session.flush()

    def test_search_keyword(self, db_session: Session) -> None:
        self._seed_multi(db_session)
        repo = UserRepository(session=db_session)
        rows, total = repo.search(keyword="user1")
        assert total == 1
        assert rows[0].username == "user1"

    def test_search_status_filter(self, db_session: Session) -> None:
        self._seed_multi(db_session)
        repo = UserRepository(session=db_session)
        rows, total = repo.search(status="disabled")
        assert total == 1
        assert rows[0].status == "disabled"

    def test_search_pagination(self, db_session: Session) -> None:
        self._seed_multi(db_session)
        repo = UserRepository(session=db_session)
        rows, total = repo.search(skip=0, limit=2)
        assert total == 3
        assert len(rows) == 2

    def test_soft_delete_excludes_from_base_query(self, db_session: Session) -> None:
        self._seed_multi(db_session)
        repo = UserRepository(session=db_session)
        assert repo.delete(1) is True
        # get_by_id 走软删过滤，查不到
        assert repo.get_by_id(1) is None
        # 但按用户名唯一性校验仍能查到（含软删除）
        assert repo.get_by_username("user0") is not None

    def test_delete_missing_returns_false(self, db_session: Session) -> None:
        repo = UserRepository(session=db_session)
        assert repo.delete(999) is False

    def test_update_last_login(self, db_session: Session) -> None:
        self._seed_multi(db_session)
        repo = UserRepository(session=db_session)
        now = datetime(2024, 1, 1, 12, 0, 0)
        repo.update_last_login(1, now, "1.1.1.1")
        db_session.flush()
        user = repo.get_by_id(1)
        assert user.last_login_at == now
        assert user.last_login_ip == "1.1.1.1"
