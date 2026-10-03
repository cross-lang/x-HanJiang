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
from typing import TYPE_CHECKING, Any

from fastapi import UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from src.constants.enums import NotificationEvent
from src.constants.permissions import PermissionAction
from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger
from src.infras.storage import StorageProvider, get_cached_storage_provider
from src.models.entities.file_entity import FileEntity
from src.repositories.file_repository import FileRepository

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher


class FileStorageService:
    """文件存储服务（业务层）。
    仅调用 FileRepository 存取数据，不直接操作数据库会话。
    """

    entity_type: str = "file"  # 审计日志实体类型

    def __init__(
        self,
        file_repository: FileRepository,
        provider: StorageProvider | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self._provider = provider or get_cached_storage_provider()
        self._repository = file_repository
        self._dispatcher = dispatcher
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
        self._repository.create(entity)
        self._repository.commit()
        self._audit(
            entity_id=entity.id,
            action=PermissionAction.UPLOAD.mark,
            operator=operator,
            after_data={"filename": file_name, "key": result.key, "size": result.size, "folder": folder},
            remarks=f"上传文件{file_name}",
        )
        logger.info(f"File uploaded: key={result.key} size={result.size} operator_id={uploaded_by} file_id={entity.id}")
        return {
            "id": entity.id,
            "filename": file_name,
            "key": result.key,
            "path": result.key,
            "url": result.url,
            "size": result.size,
            "storage": result.storage,
            "content_type": content_type,
            "uploaded_by": uploaded_by,
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
        """查询文件列表（分页，经仓库）。"""
        skip = (page - 1) * page_size
        rows, total = self._repository.list_files(
            folder=folder,
            uploaded_by=uploaded_by,
            keyword=keyword,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [
                {
                    "id": r[0].id,
                    "original_name": r[0].original_name,
                    "extension": r[0].extension,
                    "mime_type": r[0].mime_type,
                    "size_bytes": r[0].size_bytes,
                    "folder": r[0].folder,
                    "storage_type": r[0].storage_type,
                    "url": r[0].url,
                    "uploaded_by": r[0].uploaded_by,
                    "uploader_name": r[1].name if r[1] else None,
                    "uploader_display": f"{r[1].name}（{r[1].username}）" if r[1] else str(r[0].uploaded_by or ""),
                    "is_public": r[0].is_public,
                    "created_at": r[0].created_at.strftime("%Y-%m-%d %H:%M:%S") if r[0].created_at else None,
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

    def download_file(
        self,
        file_path: str,
        operator: dict[str, Any] | None = None,
    ) -> FileResponse | RedirectResponse | StreamingResponse:
        normalized_path = file_path.strip("/")
        if not normalized_path or ".." in Path(normalized_path).parts:
            raise ValidationException(message="文件路径无效")
        filename = Path(normalized_path).name
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self._audit(
            entity_id=normalized_path,
            action=PermissionAction.DOWNLOAD.mark,
            operator=operator,
            remarks=f"下载文件{filename}",
        )
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
            f"attachment; filename=\"download{Path(filename).suffix}\"; filename*=UTF-8''{encoded_filename}"
        )
        return FileResponse(
            path=file_full_path,
            media_type=media_type,
            filename=filename,
            headers={"Content-Disposition": content_disposition},
        )

    # ── 删除（软删除）───────────────────────────────────

    def delete_file(self, file_id: int, operator: dict[str, Any] | None = None) -> bool:
        """软删除文件记录（不真删存储里的文件，经仓库）。"""
        entity = self._repository.soft_delete(file_id)
        if entity is None:
            raise NotFoundException(message=f"文件 {file_id} 不存在")
        # 删除前先记录上传者和文件名
        uploaded_by = entity.uploaded_by
        filename = entity.original_name
        self._repository.commit()
        self._audit(
            entity_id=file_id,
            action=PermissionAction.DELETE.mark,
            operator=operator,
            before_data={"filename": filename, "uploaded_by": uploaded_by},
            remarks=f"删除文件{filename}",
        )
        logger.info(f"File soft-deleted: id={file_id} key={entity.file_key}")
        # 文件删除通知给上传者（经构造注入的 dispatcher，失败不阻断）
        if uploaded_by and self._dispatcher is not None:
            try:
                self._dispatcher.dispatch_for_user(
                    user_id=uploaded_by,
                    event_type=NotificationEvent.FILE_DELETED,
                    variables={"filename": filename, "operator": operator.get("operator_name") if operator else ""},
                )
            except Exception:  # noqa: BLE001
                logger.warning("文件删除通知发送失败 file_id=%s", file_id)
        return True

    # ── 统计 ────────────────────────────────────────────

    def get_storage_stats(self) -> dict[str, Any]:
        """获取存储用量统计（经仓库）。"""
        total_size, total_count, by_folder = self._repository.get_storage_stats()
        return {
            "total_size_bytes": total_size,
            "total_count": total_count,
            "by_folder": [{"folder": r[0], "count": r[1], "size_bytes": r[2]} for r in by_folder],
        }

    def _audit(
        self,
        entity_id: Any,
        action: str,
        operator: dict[str, Any] | None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        remarks: str | None = None,
    ) -> None:
        """记录审计日志（失败不影响主流程）。

        Args:
            entity_id: 实体主键
            action: 操作类型（upload / download / delete 等）
            operator: 操作人上下文（operator_id / operator_name / ip_address）
            before_data: 变更前数据快照
            after_data: 变更后数据快照
            remarks: 备注说明
        """
        try:
            from src.services.admin.audit_service import AuditService

            AuditService().log_event(
                entity_type=self.entity_type,
                entity_id=entity_id,
                action=action,
                operator_id=operator.get("operator_id") if operator else None,
                before_data=before_data,
                after_data=after_data,
                ip_address=operator.get("ip_address") if operator else None,
                remarks=remarks or f"{self.entity_type} {action}",
            )
        except Exception as exc:  # noqa: BLE001 - 审计失败不阻断主流程
            logger.warning("审计日志写入失败 entity_type=%s action=%s: %s", self.entity_type, action, exc)
