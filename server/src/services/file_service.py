#!/usr/bin/env python3
"""文件存储和管理服务。

通过 StorageProvider 抽象层实现，业务代码不关心底层存储是本地还是七牛。
切换存储实现只需修改配置文件，无需改动任何业务代码。
上传时同步记录文件元数据到 files 表。
"""

from __future__ import annotations

import mimetypes
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy import func, select

from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger
from src.infras.database import get_cached_database_provider
from src.infras.storage import StorageProvider, get_cached_storage_provider
from src.models.entities.file_entity import FileEntity


class FileStorageService:
    """文件存储服务（业务层）。"""

    def __init__(self, provider: StorageProvider | None = None) -> None:
        self._provider = provider or get_cached_storage_provider()
        self._session = get_cached_database_provider().get_session_factory()()
        logger.info(f"FileStorageService initialized with provider: {type(self._provider).__name__}")

    # ── 上传 ────────────────────────────────────────────

    def save_upload(
        self,
        file: UploadFile,
        folder: str = "general",
        operator: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """保存上传文件，并记录到 files 表。"""
        file_name = file.filename or "upload.bin"
        content_type = file.content_type or "application/octet-stream"
        key = self._provider.make_object_key(folder, file_name)
        data = file.file.read()

        result = self._provider.upload_file(data, key, content_type=content_type)

        # 记录到数据库
        ext = Path(file_name).suffix.lstrip(".")
        uploaded_by = operator.get("operator_id") if operator else None
        entity = FileEntity(
            file_key=result.key,
            original_name=file_name,
            stored_name=Path(result.key).name,
            extension=ext,
            mime_type=content_type,
            size_bytes=result.size,
            folder=folder,
            storage_type=result.storage,
            url=result.url,
            uploaded_by=uploaded_by,
        )
        self._session.add(entity)
        self._session.commit()

        logger.info(
            f"File uploaded: key={result.key} size={result.size} "
            f"operator_id={uploaded_by} file_id={entity.id}"
        )

        return {
            "id": entity.id,
            "filename": file_name,
            "key": result.key,
            "path": result.key,
            "url": result.url,
            "size": result.size,
            "storage": result.storage,
            "content_type": content_type,
        }

    # ── 列表 ────────────────────────────────────────────

    def list_files(
        self,
        folder: str | None = None,
        uploaded_by: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """查询文件列表（分页）。"""
        stmt = select(FileEntity).where(FileEntity.is_deleted == False)
        count_stmt = select(func.count(FileEntity.id)).where(FileEntity.is_deleted == False)

        if folder:
            stmt = stmt.where(FileEntity.folder == folder)
            count_stmt = count_stmt.where(FileEntity.folder == folder)
        if uploaded_by:
            stmt = stmt.where(FileEntity.uploaded_by == uploaded_by)
            count_stmt = count_stmt.where(FileEntity.uploaded_by == uploaded_by)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(FileEntity.original_name.like(like))
            count_stmt = count_stmt.where(FileEntity.original_name.like(like))

        total = self._session.execute(count_stmt).scalar() or 0
        rows = self._session.execute(
            stmt.order_by(FileEntity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()

        return {
            "items": [
                {
                    "id": r.id,
                    "original_name": r.original_name,
                    "extension": r.extension,
                    "mime_type": r.mime_type,
                    "size_bytes": r.size_bytes,
                    "folder": r.folder,
                    "storage_type": r.storage_type,
                    "url": r.url,
                    "uploaded_by": r.uploaded_by,
                    "is_public": r.is_public,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── 下载 ────────────────────────────────────────────

    def get_url(self, key: str) -> str:
        return self._provider.get_download_url(key)

    def download_file(self, file_path: str) -> FileResponse | RedirectResponse | StreamingResponse:
        normalized_path = file_path.strip("/")
        if not normalized_path or ".." in Path(normalized_path).parts:
            raise ValidationException(message="文件路径无效")

        filename = Path(normalized_path).name
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        provider_name = type(self._provider).__name__
        if provider_name != "LocalStorage":
            if not self._provider.file_exists(normalized_path):
                raise NotFoundException(message="文件不存在")
            download_url = self._provider.get_download_url(normalized_path, expires=3600)
            return RedirectResponse(url=download_url, status_code=302)

        from src.core.config import settings

        base_dir = Path(settings.storage.local.base_dir).resolve()
        file_full_path = (base_dir / normalized_path).resolve()
        try:
            file_full_path.relative_to(base_dir)
        except ValueError as exc:
            raise ValidationException(message="文件路径无效") from exc
        if not file_full_path.is_file():
            raise NotFoundException(message="文件不存在")

        encoded_filename = urllib.parse.quote(filename, safe="")
        content_disposition = (
            f'attachment; filename="download{Path(filename).suffix}"; '
            f"filename*=UTF-8''{encoded_filename}"
        )
        return FileResponse(
            path=file_full_path,
            media_type=media_type,
            filename=filename,
            headers={"Content-Disposition": content_disposition},
        )

    # ── 删除（软删除）───────────────────────────────────

    def delete_file(self, file_id: int) -> bool:
        """软删除文件记录（不真删存储里的文件）。"""
        entity = self._session.get(FileEntity, file_id)
        if entity is None:
            raise NotFoundException(message=f"文件 {file_id} 不存在")
        entity.is_deleted = True
        self._session.commit()
        logger.info(f"File soft-deleted: id={file_id} key={entity.file_key}")
        return True

    # ── 统计 ────────────────────────────────────────────

    def get_storage_stats(self) -> dict[str, Any]:
        """获取存储用量统计。"""
        total_size = self._session.execute(
            select(func.coalesce(func.sum(FileEntity.size_bytes), 0)).where(
                FileEntity.is_deleted == False
            )
        ).scalar() or 0
        total_count = self._session.execute(
            select(func.count(FileEntity.id)).where(FileEntity.is_deleted == False)
        ).scalar() or 0
        by_folder = self._session.execute(
            select(FileEntity.folder, func.count(FileEntity.id), func.coalesce(func.sum(FileEntity.size_bytes), 0))
            .where(FileEntity.is_deleted == False)
            .group_by(FileEntity.folder)
        ).all()
        return {
            "total_size_bytes": total_size,
            "total_count": total_count,
            "by_folder": [
                {"folder": r[0], "count": r[1], "size_bytes": r[2]} for r in by_folder
            ],
        }

    def __del__(self):
        if hasattr(self, '_session'):
            self._session.close()
