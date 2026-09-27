#!/usr/bin/env python3
"""
文件数据访问实现

本模块提供文件 Repository 的 SQLAlchemy 数据库实现。
支持软删除（is_deleted）、按条件分页查询、存储用量统计。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    FileRepository: 文件数据访问 SQLAlchemy 实现
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import DatabaseException
from src.models.entities.file_entity import FileEntity
from src.models.entities.user_entity import UserEntity
from src.repositories.base_repository import BaseRepository


class FileRepository(BaseRepository[FileEntity, int]):
    """文件数据访问 SQLAlchemy 实现。"""

    model_class = FileEntity

    def _base_query(self):
        """排除已删除文件。"""
        return select(FileEntity).where(FileEntity.is_deleted == False)  # noqa: E712

    # ── 业务查询 ──────────────────────────────────────────

    def list_files(
        self,
        folder: str | None = None,
        uploaded_by: int | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        """分页查询文件列表（关联上传人姓名）。

        Returns:
            tuple[list, int]: (行列表[(FileEntity, UserEntity|None)], 总数)
        """
        conditions = [FileEntity.is_deleted == False]  # noqa: E712
        if folder:
            conditions.append(FileEntity.folder == folder)
        if uploaded_by:
            conditions.append(FileEntity.uploaded_by == uploaded_by)
        if keyword:
            conditions.append(FileEntity.original_name.like(f"%{keyword}%"))

        total = (
            self.session.execute(
                select(func.count(FileEntity.id)).where(*conditions)
            ).scalar()
            or 0
        )
        stmt = (
            select(FileEntity, UserEntity)
            .outerjoin(UserEntity, UserEntity.id == FileEntity.uploaded_by)
            .where(*conditions)
            .order_by(FileEntity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = self.session.execute(stmt).all()
        return rows, total

    def get_storage_stats(self) -> tuple[int, int, list]:
        """获取存储用量统计。

        Returns:
            tuple[int, int, list]: (总大小, 总数, 按文件夹行列表[(folder, count, size)])
        """
        total_size = (
            self.session.execute(
                select(func.coalesce(func.sum(FileEntity.size_bytes), 0)).where(
                    FileEntity.is_deleted == False  # noqa: E712
                )
            ).scalar()
            or 0
        )
        total_count = (
            self.session.execute(
                select(func.count(FileEntity.id)).where(
                    FileEntity.is_deleted == False  # noqa: E712
                )
            ).scalar()
            or 0
        )
        by_folder = self.session.execute(
            select(
                FileEntity.folder,
                func.count(FileEntity.id),
                func.coalesce(func.sum(FileEntity.size_bytes), 0),
            )
            .where(FileEntity.is_deleted == False)  # noqa: E712
            .group_by(FileEntity.folder)
        ).all()
        return total_size, total_count, by_folder

    # ── 写入 ──────────────────────────────────────────────

    def soft_delete(self, id: int) -> FileEntity | None:
        """软删除文件记录，返回删除前的实体（用于通知）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return None
        existing.is_deleted = True
        try:
            self.session.flush()
            return existing
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除文件失败: {e}") from e
