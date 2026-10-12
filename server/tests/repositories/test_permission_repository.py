#!/usr/bin/env python3
"""权限仓储（PermissionRepository）单元测试。

覆盖：
    - 按权限编码查询
    - 按关键字/模块/操作搜索分页（仅未废弃）
    - 全部去重模块/操作列表
    - exists_permission_in 判断
"""

from sqlalchemy.orm import Session
from src.models.entities.user_entity import PermissionEntity
from src.repositories.permission_repository import PermissionRepository


def _make_perm(
    perm_id: int,
    code: str,
    name: str,
    module: str,
    operation: str,
    deprecated: bool = False,
    sort_order: int = 0,
) -> PermissionEntity:
    return PermissionEntity(
        id=perm_id,
        perm_code=code,
        perm_name=name,
        module=module,
        operation=operation,
        description=None,
        sort_order=sort_order,
        is_deprecated=deprecated,
    )


def _seed(db_session: Session) -> None:
    db_session.add(_make_perm(1, "user:view", "查看用户", "user", "view", sort_order=1))
    db_session.add(_make_perm(2, "user:create", "创建用户", "user", "create", sort_order=2))
    db_session.add(_make_perm(3, "role:view", "查看角色", "role", "view", sort_order=3))
    db_session.add(_make_perm(4, "legacy:x", "废弃权限", "user", "view", deprecated=True))
    db_session.flush()


class TestPermissionQueries:
    def test_get_by_code(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        assert repo.get_by_code("user:view").perm_name == "查看用户"
        assert repo.get_by_code("missing") is None

    def test_search_keyword(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        rows, total = repo.search(keyword="创建")
        assert total == 1
        assert rows[0].perm_code == "user:create"

    def test_search_module_and_operation(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        rows, total = repo.search(module="role", operation="view")
        assert total == 1
        assert rows[0].perm_code == "role:view"

    def test_search_excludes_deprecated(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        rows, total = repo.search()
        # 废弃权限 legacy:x 不出现
        assert total == 3
        assert all(not p.is_deprecated for p in rows)

    def test_search_pagination_and_order(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        rows, total = repo.search(skip=0, limit=2)
        assert total == 3
        assert len(rows) == 2
        # 按 sort_order 升序
        assert [p.sort_order for p in rows] == [1, 2]

    def test_get_all_modules(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        assert repo.get_all_modules() == ["role", "user"]

    def test_get_all_operations(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        assert repo.get_all_operations() == ["create", "view"]


class TestExistsPermissionIn:
    def test_empty_ids_returns_false(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        assert repo.exists_permission_in([], "user:view") is False

    def test_code_in_ids(self, db_session: Session) -> None:
        _seed(db_session)
        repo = PermissionRepository(session=db_session)
        assert repo.exists_permission_in([1, 2], "user:view") is True
        assert repo.exists_permission_in([1, 2], "role:view") is False
