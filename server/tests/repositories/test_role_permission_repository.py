#!/usr/bin/env python3
"""角色权限关联仓储（RolePermissionRepository）单元测试。

覆盖：
    - 按角色查权限 ID 列表 / 权限实体（按 sort_order 排序）
    - 绑定权限、解绑权限（不存在/存在）
    - create 委托 add_permission、update 仅回读
"""

from sqlalchemy.orm import Session
from src.models.entities.user_entity import PermissionEntity, RolePermissionEntity
from src.repositories.role_permission_repository import RolePermissionRepository


def _make_perm(perm_id: int, code: str, sort_order: int = 0) -> PermissionEntity:
    return PermissionEntity(
        id=perm_id,
        perm_code=code,
        perm_name=code,
        module="user",
        operation="view",
        sort_order=sort_order,
        is_deprecated=False,
    )


def _seed(db_session: Session) -> None:
    db_session.add(_make_perm(1, "user:view", sort_order=2))
    db_session.add(_make_perm(2, "user:create", sort_order=1))
    db_session.add(RolePermissionEntity(role_id=10, permission_id=1))
    db_session.add(RolePermissionEntity(role_id=10, permission_id=2))
    db_session.flush()


class TestRolePermissionQueries:
    def test_get_permission_ids_by_role(self, db_session: Session) -> None:
        _seed(db_session)
        repo = RolePermissionRepository(session=db_session)
        assert set(repo.get_permission_ids_by_role(10)) == {1, 2}
        assert repo.get_permission_ids_by_role(999) == []

    def test_get_permissions_by_role_ordered(self, db_session: Session) -> None:
        _seed(db_session)
        repo = RolePermissionRepository(session=db_session)
        perms = repo.get_permissions_by_role(10)
        # 按 sort_order 升序：2(user:create) 在 1(user:view) 前
        assert [p.perm_code for p in perms] == ["user:create", "user:view"]


class TestRolePermissionBind:
    def test_add_permission(self, db_session: Session) -> None:
        db_session.add(_make_perm(3, "user:delete"))
        db_session.flush()
        repo = RolePermissionRepository(session=db_session)
        entity = repo.add_permission(10, 3)
        assert entity.role_id == 10 and entity.permission_id == 3
        assert 3 in repo.get_permission_ids_by_role(10)

    def test_create_delegates_add(self, db_session: Session) -> None:
        db_session.add(_make_perm(3, "user:delete"))
        db_session.flush()
        repo = RolePermissionRepository(session=db_session)
        entity = repo.create(RolePermissionEntity(role_id=10, permission_id=3))
        assert entity.permission_id == 3

    def test_remove_not_bound_returns_false(self, db_session: Session) -> None:
        _seed(db_session)
        repo = RolePermissionRepository(session=db_session)
        assert repo.remove_permission(10, 999) is False

    def test_remove_bound_returns_true(self, db_session: Session) -> None:
        _seed(db_session)
        repo = RolePermissionRepository(session=db_session)
        assert repo.remove_permission(10, 1) is True
        assert 1 not in repo.get_permission_ids_by_role(10)

    def test_update_reads_back(self, db_session: Session) -> None:
        _seed(db_session)
        repo = RolePermissionRepository(session=db_session)
        # update 仅回读：先取一条关联记录的 id
        rows = db_session.query(RolePermissionEntity).filter_by(role_id=10).all()
        rid = rows[0].id
        assert repo.update(rid, RolePermissionEntity()) is not None
