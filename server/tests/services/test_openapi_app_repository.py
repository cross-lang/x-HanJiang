#!/usr/bin/env python3
"""开放应用仓库测试（src/repositories/openapi_app_repository.py）。

以 FakeSession 替身验证仓库方法对 SQLAlchemy 会话的编排逻辑：
    - 查询：get_by_app_id / find_by_name_owner / search_by_keyword / 归属方查询
    - 写入：touch_last_used（成功刷新 / 异常回滚）、soft_delete、按归属方批量启停/软删
不连接真实数据库，execute/get 仅返回预设结果并记录调用。
"""

import pytest
from src.models.entities.app_entity import OpenApiAppEntity
from src.repositories.openapi_app_repository import OpenApiAppRepository


class FakeSession:
    """可编排返回值的会话替身（execute 链式 .scalars()/.scalar_one()/.rowcount）。"""

    def __init__(self) -> None:
        self.executed: list = []
        self.gets: list[tuple] = []
        self.flushed: int = 0
        self.rolled_back: int = 0
        # 预设返回
        self.execute_first = None
        self.execute_all: list = []
        self.execute_scalar_one: int = 0
        self.execute_rowcount: int = 0
        self.execute_raises: Exception | None = None
        self.get_result = None

    # ── 会话协议 ──────────────────────────────────────
    def execute(self, stmt):
        if self.execute_raises is not None:
            raise self.execute_raises
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

    def flush(self) -> None:
        self.flushed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


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


def _make_repo() -> tuple[OpenApiAppRepository, FakeSession]:
    session = FakeSession()
    repo = OpenApiAppRepository(session=session)
    return repo, session


class TestQuery:
    """查询方法编排。"""

    def test_get_by_app_id_returns_first(self) -> None:
        """按 AppId 查询返回 scalars().first()。"""
        repo, session = _make_repo()
        app = _make_app()
        session.execute_first = app
        assert repo.get_by_app_id("hj_test_1") is app

    def test_find_by_name_owner_returns_first(self) -> None:
        """按名称+归属方查询返回 first()。"""
        repo, session = _make_repo()
        app = _make_app()
        session.execute_first = app
        assert repo.find_by_name_owner("应用1", "developer", 7) is app

    def test_search_by_keyword_returns_rows_and_total(self) -> None:
        """关键字分页：返回 (行列表, 总数)。"""
        repo, session = _make_repo()
        apps = [_make_app(1), _make_app(2)]
        session.execute_all = apps
        session.execute_scalar_one = 2
        rows, total = repo.search_by_keyword(keyword="应用", skip=0, limit=20)
        assert rows == apps
        assert total == 2

    def test_search_by_keyword_with_owner_filter(self) -> None:
        """同时传入 owner_type / owner_id：归属过滤条件被组装（不报错）。"""
        repo, session = _make_repo()
        session.execute_all = [_make_app(1)]
        session.execute_scalar_one = 1
        rows, total = repo.search_by_keyword(keyword="应用", owner_type="developer", owner_id=7, skip=0, limit=20)
        assert total == 1
        assert len(rows) == 1

    def test_get_owner_user_via_session_get(self) -> None:
        """查询归属管理员走 session.get(UserEntity, id)。"""
        repo, session = _make_repo()
        fake_user = object()
        session.get_result = fake_user
        assert repo.get_owner_user(5) is fake_user
        assert session.gets[0][1] == 5

    def test_get_owner_developer_via_session_get(self) -> None:
        """查询归属开发者走 session.get(DeveloperEntity, id)。"""
        repo, session = _make_repo()
        fake_dev = object()
        session.get_result = fake_dev
        assert repo.get_owner_developer(7) is fake_dev
        assert session.gets[0][1] == 7

    def test_list_user_ids_by_perm(self) -> None:
        """按权限码查询用户 ID 列表。"""
        repo, session = _make_repo()
        session.execute_all = [1, 2, 3]
        assert repo.list_user_ids_by_perm("openapi_app.approve") == [1, 2, 3]

    def test_list_active_scopes(self) -> None:
        """查询未废弃 scope 列表。"""
        repo, session = _make_repo()
        scope_objs = [object(), object()]
        session.execute_all = scope_objs
        assert repo.list_active_scopes() == scope_objs


class TestWrite:
    """写入/状态变更方法。"""

    def test_touch_last_used_sets_time_and_flushes(self) -> None:
        """成功命中应用：更新 last_used_at 并 flush。"""
        repo, session = _make_repo()
        app = _make_app()
        session.execute_first = app
        repo.touch_last_used("hj_test_1")
        assert app.last_used_at is not None
        assert session.flushed == 1

    def test_touch_last_used_missing_app_no_flush(self) -> None:
        """应用不存在：直接返回，不 flush。"""
        repo, session = _make_repo()
        session.execute_first = None
        repo.touch_last_used("hj_test_x")
        assert session.flushed == 0

    def test_touch_last_used_exception_triggers_rollback(self) -> None:
        """刷新异常：回滚且不抛错。"""
        repo, session = _make_repo()
        session.execute_raises = RuntimeError("db down")
        repo.touch_last_used("hj_test_1")
        assert session.rolled_back == 1

    def test_soft_delete_existing(self) -> None:
        """软删存在的应用：置 deleted_at 并 flush，返回 True。"""
        repo, session = _make_repo()
        app = _make_app()
        # get_by_id 走 _base_query().scalars().first()
        session.execute_first = app
        assert repo.soft_delete(1) is True
        assert app.deleted_at is not None
        assert session.flushed == 1

    def test_soft_delete_missing_returns_false(self) -> None:
        """软删不存在的应用：返回 False。"""
        repo, session = _make_repo()
        session.execute_first = None
        assert repo.soft_delete(999) is False

    def test_update_status_by_owner_returns_rowcount(self) -> None:
        """按归属方批量启停：返回受影响行数。"""
        repo, session = _make_repo()
        session.execute_rowcount = 3
        assert repo.update_status_by_owner("developer", 7, "disabled") == 3

    def test_soft_delete_by_owner_returns_rowcount(self) -> None:
        """按归属方批量软删：返回受影响行数。"""
        repo, session = _make_repo()
        session.execute_rowcount = 2
        assert repo.soft_delete_by_owner("developer", 7) == 2


class TestIntegrityError:
    """唯一约束冲突处理。"""

    def test_handle_integrity_error_conflict(self) -> None:
        """AppId 冲突 → 抛 ConflictException，附带底层错误信息。"""
        from types import SimpleNamespace

        from src.core.exceptions import ConflictException

        repo, _ = _make_repo()
        fake_error = SimpleNamespace(orig="duplicate key value")
        with pytest.raises(ConflictException, match="AppId 已存在"):
            repo._handle_integrity_error(fake_error, _make_app())
