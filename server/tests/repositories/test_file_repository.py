#!/usr/bin/env python3
"""文件仓储（FileRepository）单元测试。

内存 SQLite 执行真实查询，覆盖：
    - list_files：文件夹/上传人/关键字过滤、关联上传人、分页、排除软删
    - get_storage_stats：总大小/总数/按文件夹聚合
    - soft_delete：标记软删并回读，缺失返回 None
不连接真实 MySQL。
"""

from sqlalchemy.orm import Session
from src.models.entities.file_entity import FileEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.file_repository import FileRepository


def _file(
    fid: int,
    key: str,
    name: str,
    size: int = 10,
    folder: str = "general",
    uploaded_by: int | None = None,
) -> FileEntity:
    return FileEntity(
        id=fid,
        file_key=key,
        original_name=name,
        stored_name=name,
        extension=name.rsplit(".", 1)[-1] if "." in name else None,
        mime_type="application/octet-stream",
        size_bytes=size,
        folder=folder,
        storage_type="local",
        url=None,
        uploaded_by=uploaded_by,
        is_deleted=False,
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


class TestListFiles:
    """文件列表查询。"""

    def _seed(self, db_session: Session) -> None:
        db_session.add(_user(7, "zhangsan", "张三"))
        db_session.add(_file(1, "k1", "cat.png", size=100, folder="general", uploaded_by=7))
        db_session.add(_file(2, "k2", "dog.png", size=200, folder="avatars"))
        db_session.add(_file(3, "k3", "cat2.jpg", size=300, folder="general"))
        db_session.flush()

    def test_list_all_join_user(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = FileRepository(session=db_session)
        rows, total = repo.list_files()
        assert total == 3
        # id=1 关联上传人 7 → (FileEntity, UserEntity)
        by_id = {r[0].id: r for r in rows}
        assert by_id[1][1].username == "zhangsan"
        # id=2 无上传人 → outer join 第二列为 None
        assert by_id[2][1] is None

    def test_filter_by_folder(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = FileRepository(session=db_session)
        rows, total = repo.list_files(folder="avatars")
        assert total == 1
        assert rows[0][0].id == 2

    def test_filter_by_uploaded_by(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = FileRepository(session=db_session)
        rows, total = repo.list_files(uploaded_by=7)
        assert total == 1
        assert rows[0][0].id == 1

    def test_filter_by_keyword(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = FileRepository(session=db_session)
        rows, total = repo.list_files(keyword="cat")
        # cat.png 与 cat2.jpg 命中
        assert total == 2

    def test_pagination(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = FileRepository(session=db_session)
        rows, total = repo.list_files(skip=0, limit=2)
        assert total == 3
        assert len(rows) == 2

    def test_soft_deleted_excluded(self, db_session: Session) -> None:
        self._seed(db_session)
        repo = FileRepository(session=db_session)
        repo.soft_delete(1)
        db_session.flush()
        _, total = repo.list_files()
        assert total == 2


class TestStorageStats:
    """存储用量统计。"""

    def test_stats_aggregate(self, db_session: Session) -> None:
        db_session.add(_file(1, "k1", "a.png", size=100, folder="general"))
        db_session.add(_file(2, "k2", "b.png", size=150, folder="general"))
        db_session.add(_file(3, "k3", "c.png", size=50, folder="avatars"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        total_size, total_count, by_folder = repo.get_storage_stats()
        assert total_size == 300
        assert total_count == 3
        aggregated = {row[0]: (row[1], row[2]) for row in by_folder}
        assert aggregated["general"] == (2, 250)
        assert aggregated["avatars"] == (1, 50)


class TestSoftDelete:
    """软删除。"""

    def test_soft_delete_returns_entity(self, db_session: Session) -> None:
        db_session.add(_file(1, "k1", "a.png"))
        db_session.flush()
        repo = FileRepository(session=db_session)
        entity = repo.soft_delete(1)
        assert entity is not None
        assert entity.is_deleted is True

    def test_soft_delete_missing_returns_none(self, db_session: Session) -> None:
        repo = FileRepository(session=db_session)
        assert repo.soft_delete(999) is None
