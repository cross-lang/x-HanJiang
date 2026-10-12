#!/usr/bin/env python3
"""审计日志仓储（AuditLogRepository）单元测试。

内存 SQLite 执行真实查询，覆盖：
    - get_user_map_by_ids：空集合 / 按 ID 批量映射
    - search：entity_type/action/operator_id/时间范围/关键字（含操作人姓名子查询）
    - update：只读回读
不连接真实 MySQL。
"""

from datetime import datetime

from sqlalchemy.orm import Session
from src.models.entities.audit_entity import AuditLogEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.audit_log_repository import AuditLogRepository


def _audit(
    aid: int,
    entity_type: str = "user",
    action: str = "create",
    operator_id: int | None = 7,
    remarks: str = "备注",
    created_at: datetime | None = None,
) -> AuditLogEntity:
    return AuditLogEntity(
        id=aid,
        entity_type=entity_type,
        entity_id=str(aid),
        action=action,
        operator_id=operator_id,
        ip_address="1.1.1.1",
        remarks=remarks,
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0),
    )


def _user(uid: int, username: str, name: str) -> UserEntity:
    return UserEntity(
        id=uid,
        username=username,
        email=f"{username}@example.com",
        name=name,
        password_hash="x",
        status="enabled",
    )


class TestUserMap:
    """操作人批量映射。"""

    def test_empty_ids(self, db_session: Session) -> None:
        repo = AuditLogRepository(session=db_session)
        assert repo.get_user_map_by_ids([]) == {}

    def test_map_by_ids(self, db_session: Session) -> None:
        db_session.add(_user(7, "zhangsan", "张三"))
        db_session.add(_user(8, "lisi", "李四"))
        db_session.flush()
        repo = AuditLogRepository(session=db_session)
        m = repo.get_user_map_by_ids([7, 8, 999])
        assert set(m) == {7, 8}
        assert m[7].username == "zhangsan"


class TestSearch:
    """条件搜索。"""

    def _seed(self, db_session: Session) -> None:
        db_session.add(_user(7, "zhangsan", "张三"))
        db_session.add(_audit(1, entity_type="user", action="create", operator_id=7))
        db_session.add(_audit(2, entity_type="role", action="delete", operator_id=8, remarks="删除角色"))
        db_session.add(_audit(3, entity_type="user", action="update", operator_id=None))
        db_session.flush()

    def test_filter_entity_type(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = AuditLogRepository(session=db_session)
        rows, total = repo.search(entity_type="user")
        assert total == 2

    def test_filter_action(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = AuditLogRepository(session=db_session)
        rows, total = repo.search(action="delete")
        assert total == 1
        assert rows[0].id == 2

    def test_filter_operator_id(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = AuditLogRepository(session=db_session)
        rows, total = repo.search(operator_id=7)
        assert total == 1
        assert rows[0].id == 1

    def test_time_range(self, db_session: Session) -> None:
        db_session.add(_audit(1, created_at=datetime(2026, 1, 1)))
        db_session.add(_audit(2, created_at=datetime(2026, 6, 1)))
        db_session.flush()
        repo = AuditLogRepository(session=db_session)
        rows, total = repo.search(start_time=datetime(2026, 3, 1), end_time=datetime(2026, 12, 31))
        assert total == 1
        assert rows[0].id == 2

    def test_keyword_matches_fields(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = AuditLogRepository(session=db_session)
        # 命中 remarks="删除角色"
        rows, total = repo.search(keyword="删除")
        assert total == 1
        assert rows[0].id == 2

    def test_keyword_matches_operator_name(self, db_session: Session) -> None:
        """关键字命中操作人用户名/姓名 → 按 operator_id 反查。"""
        self._seed(db_session)
        repo = AuditLogRepository(session=db_session)
        rows, total = repo.search(keyword="zhangsan")
        assert total == 1
        assert rows[0].operator_id == 7

    def test_pagination(self, db_session: Session) -> None:
        for i in range(5):
            db_session.add(_audit(i + 1))
        db_session.flush()
        repo = AuditLogRepository(session=db_session)
        rows, total = repo.search(skip=0, limit=2)
        assert total == 5
        assert len(rows) == 2

    def test_default_order_desc(self, db_session: Session) -> None:
        """默认按 created_at 倒序。"""
        db_session.add(_audit(1, created_at=datetime(2026, 1, 1)))
        db_session.add(_audit(2, created_at=datetime(2026, 2, 1)))
        db_session.flush()
        repo = AuditLogRepository(session=db_session)
        rows, _ = repo.search()
        assert rows[0].id == 2


class TestReadOnly:
    """审计日志只读。"""

    def test_update_returns_get_by_id(self, db_session: Session) -> None:
        db_session.add(_audit(1))
        db_session.flush()
        repo = AuditLogRepository(session=db_session)
        got = repo.update(1, AuditLogEntity(remarks="篡改"))
        assert got.id == 1
