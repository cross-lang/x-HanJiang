#!/usr/bin/env python3
"""角色仓储（RoleRepository）单元测试。

覆盖：
    - 按角色编码/名称查询
    - 按用户查角色、统计角色关联用户数
    - 关键字/类型/状态搜索分页
    - 软删除
"""

from sqlalchemy.orm import Session
from src.models.entities.user_entity import RoleEntity, UserEntity, UserRoleEntity
from src.repositories.role_repository import RoleRepository


def _make_role(role_id: int, code: str, name: str, role_type: str = "custom", status: str = "enabled") -> RoleEntity:
    return RoleEntity(
        id=role_id,
        role_name=name,
        role_code=code,
        description="",
        role_type=role_type,
        status=status,
    )


class TestRoleQueries:
    def test_get_by_code(self, db_session: Session) -> None:
        db_session.add(_make_role(1, "admin", "管理员"))
        db_session.flush()
        repo = RoleRepository(session=db_session)
        assert repo.get_by_code("admin").role_name == "管理员"
        assert repo.get_by_code("missing") is None

    def test_get_by_name(self, db_session: Session) -> None:
        db_session.add(_make_role(1, "admin", "管理员"))
        db_session.flush()
        repo = RoleRepository(session=db_session)
        assert repo.get_by_name("管理员").role_code == "admin"

    def test_get_by_user_id(self, db_session: Session) -> None:
        db_session.add(_make_role(1, "admin", "管理员"))
        db_session.add(_make_role(2, "user", "普通用户"))
        db_session.add(UserEntity(id=1, username="u", email="u@example.com", name="u", password_hash="x"))
        db_session.add(UserRoleEntity(user_id=1, role_id=1))
        db_session.flush()
        repo = RoleRepository(session=db_session)
        roles = repo.get_by_user_id(1)
        assert [r.role_code for r in roles] == ["admin"]

    def test_count_user_links(self, db_session: Session) -> None:
        db_session.add(_make_role(1, "admin", "管理员"))
        db_session.add(UserEntity(id=1, username="u1", email="u1@e.com", name="u1", password_hash="x"))
        db_session.add(UserEntity(id=2, username="u2", email="u2@e.com", name="u2", password_hash="x"))
        db_session.add(UserRoleEntity(user_id=1, role_id=1))
        db_session.add(UserRoleEntity(user_id=2, role_id=1))
        db_session.flush()
        repo = RoleRepository(session=db_session)
        assert repo.count_user_links(1) == 2
        assert repo.count_user_links(999) == 0


class TestRoleSearchAndDelete:
    def _seed(self, db_session: Session) -> None:
        db_session.add(_make_role(1, "admin", "管理员", role_type="system"))
        db_session.add(_make_role(2, "editor", "编辑", status="disabled"))
        db_session.add(_make_role(3, "viewer", "只读"))
        db_session.flush()

    def test_search_keyword(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = RoleRepository(session=db_session)
        rows, total = repo.search(keyword="编辑")
        assert total == 1
        assert rows[0].role_code == "editor"

    def test_search_filters(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = RoleRepository(session=db_session)
        rows, total = repo.search(role_type="system")
        assert total == 1
        assert rows[0].role_code == "admin"
        rows, total = repo.search(status="disabled")
        assert total == 1

    def test_search_pagination(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = RoleRepository(session=db_session)
        rows, total = repo.search(skip=0, limit=2)
        assert total == 3
        assert len(rows) == 2

    def test_soft_delete(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = RoleRepository(session=db_session)
        assert repo.delete(1) is True
        assert repo.get_by_id(1) is None
        assert repo.delete(999) is False
