#!/usr/bin/env python3
"""开放应用申请仓库测试（src/repositories/openapi_app_registration_repository.py）。

以 FakeSession 替身验证申请批次仓库的编排逻辑：
    - 查询：search 联查分页、get_by_id、code_exists、find_pending/find_latest
    - 写入：reject_pending_by_app_ids（空列表短路 / 非空按 rowcount）
不连接真实数据库，execute/get 仅返回预设结果并记录调用。
"""

from datetime import UTC, datetime

from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.repositories.openapi_app_registration_repository import OpenApiAppRegistrationRepository


class FakeSession:
    """可编排返回值的会话替身。"""

    def __init__(self) -> None:
        self.executed: list = []
        self.gets: list[tuple] = []
        # 预设返回
        self.execute_first = None
        self.execute_all: list = []
        self.execute_scalar_one: int = 0
        self.execute_rowcount: int = 0
        self.get_result = None

    def execute(self, stmt):
        self.executed.append(stmt)
        return self

    def scalars(self):
        return self

    def first(self):
        return self.execute_first

    def all(self):
        return list(self.execute_all)

    def scalar_one(self):
        return self.execute_scalar_one

    @property
    def rowcount(self) -> int:
        return self.execute_rowcount

    def get(self, model, pk):
        self.gets.append((model, pk))
        return self.get_result


def _make_registration(id: int = 1, app_id: int = 1) -> OpenApiAppRegistrationEntity:
    now = datetime.now(UTC)
    return OpenApiAppRegistrationEntity(
        id=id,
        registration_code="123456",
        app_id=app_id,
        registration_type="create",
        name="应用名",
        description="描述",
        scopes="user:read",
        auth_mode="plain",
        status="pending",
        created_at=now,
        updated_at=now,
    )


def _make_app(id: int = 1) -> OpenApiAppEntity:
    return OpenApiAppEntity(
        id=id,
        app_id=f"hj_test_{id}",
        app_key_hash="x",
        name=f"应用{id}",
        description="描述",
        owner_type="developer",
        owner_id=7,
        approved=True,
        scopes="user:read",
        status="active",
        auth_mode="plain",
        rate_limit_per_minute=60,
    )


def _make_repo() -> tuple[OpenApiAppRegistrationRepository, FakeSession]:
    session = FakeSession()
    repo = OpenApiAppRegistrationRepository(session=session)
    return repo, session


class TestQuery:
    """查询方法编排。"""

    def test_search_returns_pairs_and_total(self) -> None:
        """联查分页：返回 ((申请, 应用) 列表, 总数)。"""
        repo, session = _make_repo()
        reg = _make_registration()
        app = _make_app()
        session.execute_all = [(reg, app)]
        session.execute_scalar_one = 1
        rows, total = repo.search(skip=0, limit=20)
        assert total == 1
        assert rows[0] == (reg, app)

    def test_search_with_filters(self) -> None:
        """带类型/状态/关键字过滤：各 where 条件被组装（不报错）。"""
        repo, session = _make_repo()
        reg = _make_registration()
        app = _make_app()
        session.execute_all = [(reg, app)]
        session.execute_scalar_one = 1
        rows, total = repo.search(
            keyword="应用",
            registration_type="create",
            status="pending",
            skip=0,
            limit=20,
        )
        assert total == 1
        assert len(rows) == 1

    def test_get_by_id_via_session_get(self) -> None:
        """按主键查询走 session.get。"""
        repo, session = _make_repo()
        reg = _make_registration()
        session.get_result = reg
        assert repo.get_by_id(1) is reg
        assert session.gets[0][1] == 1

    def test_code_exists_true(self) -> None:
        """申请码已占用：first() 非空 → True。"""
        repo, session = _make_repo()
        session.execute_first = (1,)
        assert repo.code_exists("123456") is True

    def test_code_exists_false(self) -> None:
        """申请码未占用：first() 为 None → False。"""
        repo, session = _make_repo()
        session.execute_first = None
        assert repo.code_exists("000000") is False

    def test_find_pending_by_app(self) -> None:
        """查询待审批申请返回 first()。"""
        repo, session = _make_repo()
        reg = _make_registration()
        session.execute_first = reg
        assert repo.find_pending_by_app(1) is reg

    def test_find_latest_by_app(self) -> None:
        """查询最近一条申请返回 first()。"""
        repo, session = _make_repo()
        reg = _make_registration()
        session.execute_first = reg
        assert repo.find_latest_by_app(1) is reg

    def test_get_app_via_session_get(self) -> None:
        """按应用 ID 查应用主表走 session.get。"""
        repo, session = _make_repo()
        app = _make_app()
        session.get_result = app
        assert repo.get_app(1) is app

    def test_list_by_app_returns_all(self) -> None:
        """列出应用全部申请批次。"""
        repo, session = _make_repo()
        regs = [_make_registration(1), _make_registration(2)]
        session.execute_all = regs
        assert repo.list_by_app(1) == regs


class TestRejectPending:
    """批量驳回待审批申请。"""

    def test_reject_empty_app_ids_short_circuits(self) -> None:
        """空 app_ids 列表：直接返回 0，不执行更新。"""
        repo, session = _make_repo()
        assert repo.reject_pending_by_app_ids([], "账号禁用") == 0
        assert session.executed == []

    def test_reject_non_empty_returns_rowcount(self) -> None:
        """非空列表：执行批量更新，返回受影响行数。"""
        repo, session = _make_repo()
        session.execute_rowcount = 2
        assert repo.reject_pending_by_app_ids([1, 2], "账号禁用") == 2
