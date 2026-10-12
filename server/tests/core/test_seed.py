#!/usr/bin/env python3
"""
种子数据模块测试（src/core/seed.py）

init_seed_data 重度依赖数据库，本测试用 Fake Session 替身（execute 一律返回空结果集），
让"权限/角色/用户/菜单/通知配置"的创建分支走完整流程，同时覆盖：
    - 获取 MySQL 锁失败 → 跳过初始化
    - 初始化过程抛异常 → 回滚并告警
    - 正常路径 → commit，且 finally 中释放锁、关闭会话
不连接真实 MySQL。
"""

import src.core.seed as seed_module


class _FakeScalarResult:
    """模拟 Session.execute(...).scalars() 的链式调用对象。"""

    def __init__(self, items: list) -> None:
        self._items = items

    def scalars(self):
        """execute(...).scalars() 本身。"""
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self) -> list:
        return list(self._items)


class FakeSession:
    """内存版 SQLAlchemy Session 替身：记录 add/flush/commit/rollback 调用。"""

    def __init__(self, *, fail_execute: bool = False) -> None:
        self.fail_execute = fail_execute
        self.added: list = []
        self.flush_count = 0
        self.committed = False
        self.rollbacked = False
        self.closed = False

    def execute(self, _query):
        if self.fail_execute:
            raise RuntimeError("模拟数据库异常")
        return _FakeScalarResult([])  # 所有查询都查不到旧数据 → 走"新建"分支

    def add(self, entity) -> None:
        self.added.append(entity)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rollbacked = True

    def close(self) -> None:
        self.closed = True


class FakeDatabaseProvider:
    """模拟数据库提供者：get_session_factory()() 返回预设 Session。"""

    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def get_session_factory(self):
        return lambda: self._session


def _patch_db(monkeypatch, session: FakeSession, *, lock_acquired: bool) -> None:
    """注入 Fake DB 提供者与命名锁函数。"""
    monkeypatch.setattr(seed_module, "get_cached_database_provider", lambda: FakeDatabaseProvider(session))
    monkeypatch.setattr(seed_module, "acquire_mysql_lock", lambda s, name, timeout=0: lock_acquired)
    monkeypatch.setattr(seed_module, "release_mysql_lock", lambda s, name: None)


class TestInitSeedData:
    """init_seed_data 主流程。"""

    def test_happy_path_creates_seed_data_and_commits(self, monkeypatch) -> None:
        """库内查不到旧数据 → 走完新建流程并 commit，会话正常关闭。"""
        session = FakeSession()
        _patch_db(monkeypatch, session, lock_acquired=True)

        seed_module.init_seed_data()

        assert session.committed is True
        assert session.closed is True
        assert session.rollbacked is False
        # 至少创建了权限、角色、用户、菜单等多类实体
        assert session.flush_count > 0
        assert len(session.added) > 0

    def test_skip_when_lock_not_acquired(self, monkeypatch) -> None:
        """抢不到 MySQL 命名锁 → 直接返回，不 commit、不建数据，但仍释放锁并关闭会话。"""
        session = FakeSession()
        _patch_db(monkeypatch, session, lock_acquired=False)

        seed_module.init_seed_data()

        assert session.committed is False
        assert session.rollbacked is False
        assert session.closed is True
        assert session.added == []

    def test_exception_triggers_rollback(self, monkeypatch) -> None:
        """执行中抛异常 → rollback 并告警，finally 仍释放锁、关闭会话。"""
        session = FakeSession(fail_execute=True)
        _patch_db(monkeypatch, session, lock_acquired=True)

        seed_module.init_seed_data()  # 不应向外抛异常

        assert session.rollbacked is True
        assert session.committed is False
        assert session.closed is True


class TestSeedMenuCatalog:
    """内置菜单目录的结构常量（纯数据校验，无副作用）。"""

    def test_each_menu_tuple_has_seven_fields(self) -> None:
        """每条菜单定义都是 (parent, title, path, icon, perm, sort, type) 七元组。"""
        for item in seed_module._SEED_MENUS:
            assert len(item) == 7

    def test_root_menus_have_zero_parent(self) -> None:
        """一级菜单的父级占位符为 0（后续按 title 解析真实 parent_id）。"""
        roots = [item for item in seed_module._SEED_MENUS if item[0] == 0]
        assert len(roots) > 0
