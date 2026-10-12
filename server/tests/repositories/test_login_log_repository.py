#!/usr/bin/env python3
"""登录日志仓储（LoginLogRepository）单元测试。

内存 SQLite 执行真实查询，覆盖：
    - search：user_id/status/login_type/时间范围/关键字过滤
    - count_recent_failures：最近 N 分钟失败计数
    - get_previous_success：按倒序 offset 取上一次成功登录
    - update 只读回读 / delete 抛 DatabaseException
不连接真实 MySQL。
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import DatabaseException
from src.models.entities.log_entity import LoginLogEntity
from src.repositories.login_log_repository import LoginLogRepository


def _log(
    lid: int,
    user_id: int = 7,
    status: str = "success",
    login_type: str = "password",
    created_at: datetime | None = None,
    ip: str = "1.1.1.1",
) -> LoginLogEntity:
    return LoginLogEntity(
        id=lid,
        user_id=user_id,
        login_type=login_type,
        ip_address=ip,
        status=status,
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0),
    )


class TestSearch:
    """条件搜索。"""

    def _seed(self, db_session: Session) -> None:
        db_session.add(_log(1, user_id=7, status="success", login_type="password"))
        db_session.add(_log(2, user_id=7, status="failed", login_type="sso"))
        db_session.add(_log(3, user_id=8, status="success", login_type="password"))
        db_session.flush()

    def test_filter_user_id(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = LoginLogRepository(session=db_session)
        rows, total = repo.search(user_id=7)
        assert total == 2

    def test_filter_status_and_type(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = LoginLogRepository(session=db_session)
        rows, total = repo.search(status="failed", login_type="sso")
        assert total == 1
        assert rows[0].id == 2

    def test_time_range(self, db_session: Session) -> None:
        db_session.add(_log(1, created_at=datetime(2026, 1, 1)))
        db_session.add(_log(2, created_at=datetime(2026, 6, 1)))
        db_session.flush()
        repo = LoginLogRepository(session=db_session)
        rows, total = repo.search(start_time=datetime(2026, 3, 1), end_time=datetime(2026, 12, 31))
        assert total == 1

    def test_keyword(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = LoginLogRepository(session=db_session)
        rows, total = repo.search(keyword="1.1.1.1")
        assert total == 3

    def test_pagination(self, db_session: Session) -> None:
        for i in range(4):
            db_session.add(_log(i + 1))
        db_session.flush()
        repo = LoginLogRepository(session=db_session)
        rows, total = repo.search(skip=0, limit=2)
        assert total == 4
        assert len(rows) == 2


class TestFailureCount:
    """最近失败计数。"""

    def test_counts_only_recent_failures(self, db_session: Session) -> None:
        now = datetime.now()
        db_session.add(_log(1, user_id=7, status="failed", created_at=now - timedelta(minutes=5)))
        db_session.add(_log(2, user_id=7, status="failed", created_at=now - timedelta(hours=5)))  # 超时
        db_session.add(_log(3, user_id=7, status="success", created_at=now - timedelta(minutes=5)))  # 成功不算
        db_session.add(_log(4, user_id=8, status="failed", created_at=now - timedelta(minutes=5)))  # 他人不算
        db_session.flush()
        repo = LoginLogRepository(session=db_session)
        assert repo.count_recent_failures(7, minutes=30) == 1


class TestPreviousSuccess:
    """上一次成功登录。"""

    def test_skip_latest_success(self, db_session: Session) -> None:
        now = datetime.now()
        db_session.add(_log(1, user_id=7, status="success", created_at=now - timedelta(minutes=10)))
        db_session.add(_log(2, user_id=7, status="success", created_at=now - timedelta(minutes=60)))
        db_session.flush()
        repo = LoginLogRepository(session=db_session)
        prev = repo.get_previous_success(7, skip=1)
        # 倒序最新是 id=1，跳过 1 条后取 id=2
        assert prev.id == 2

    def test_no_previous_returns_none(self, db_session: Session) -> None:
        repo = LoginLogRepository(session=db_session)
        assert repo.get_previous_success(7) is None


class TestReadOnly:
    """登录日志只读/不可删。"""

    def test_update_returns_get_by_id(self, db_session: Session) -> None:
        db_session.add(_log(1))
        db_session.flush()
        repo = LoginLogRepository(session=db_session)
        got = repo.update(1, LoginLogEntity(status="failed"))
        assert got.id == 1

    def test_delete_raises(self, db_session: Session) -> None:
        repo = LoginLogRepository(session=db_session)
        with pytest.raises(DatabaseException):
            repo.delete(1)
