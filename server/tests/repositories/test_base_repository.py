#!/usr/bin/env python3
"""仓储基类（BaseRepository）通用 CRUD 单元测试。

用内存 SQLite 执行真实 SQLAlchemy 语句，借 FileRepository（继承基类默认实现）覆盖：
    - get_by_id / get_all / count
    - create（含唯一约束冲突 → ConflictException）
    - update（存在 / 不存在）/ delete / commit / rollback / flush
    - _handle_integrity_error 默认冲突处理
不连接真实 MySQL。
"""

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import ConflictException
from src.models.entities.file_entity import FileEntity
from src.repositories.file_repository import FileRepository


def _make_file(fid: int, key: str, name: str = "a.png", size: int = 10, folder: str = "general") -> FileEntity:
    """构造最小可用文件实体。"""
    return FileEntity(
        id=fid,
        file_key=key,
        original_name=name,
        stored_name=name,
        extension="png",
        mime_type="image/png",
        size_bytes=size,
        folder=folder,
        storage_type="local",
        url=None,
        is_deleted=False,
    )


class TestBaseCrud:
    """通用增删改查。"""

    def test_create_and_get_by_id(self, db_session: Session) -> None:
        db_session.add(_make_file(1, "k1"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        assert repo.get_by_id(1).original_name == "a.png"
        assert repo.get_by_id(999) is None

    def test_get_all_pagination(self, db_session: Session) -> None:
        for i in range(3):
            db_session.add(_make_file(i + 1, f"k{i}"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        rows = repo.get_all(skip=1, limit=2)
        assert len(rows) == 2

    def test_count(self, db_session: Session) -> None:
        for i in range(3):
            db_session.add(_make_file(i + 1, f"k{i}"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        assert repo.count() == 3

    def test_update_updates_columns(self, db_session: Session) -> None:
        db_session.add(_make_file(1, "k1", name="old.png"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        updated = repo.update(1, FileEntity(original_name="new.png"))
        assert updated.original_name == "new.png"
        assert repo.get_by_id(1).original_name == "new.png"

    def test_update_missing_returns_none(self, db_session: Session) -> None:
        repo = FileRepository(session=db_session)
        assert repo.update(999, FileEntity(original_name="x")) is None

    def test_delete_physical(self, db_session: Session) -> None:
        db_session.add(_make_file(1, "k1"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        assert repo.delete(1) is True
        assert repo.get_by_id(1) is None

    def test_delete_missing_returns_false(self, db_session: Session) -> None:
        repo = FileRepository(session=db_session)
        assert repo.delete(999) is False

    def test_commit_rollback_flush_no_crash(self, db_session: Session) -> None:
        """commit/rollback/flush 透传会话，不应抛错。"""
        repo = FileRepository(session=db_session)
        repo.commit()
        repo.rollback()
        repo.flush()

    def test_duplicate_key_conflict(self, db_session: Session) -> None:
        """file_key 唯一约束冲突 → 基类默认 ConflictException。"""
        repo = FileRepository(session=db_session)
        repo.create(_make_file(1, "same-key"))
        db_session.commit()
        with pytest.raises(ConflictException):
            repo.create(_make_file(2, "same-key"))
