#!/usr/bin/env python3
"""文件存储和管理服务。"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from fastapi.responses import FileResponse, StreamingResponse

try:
    import boto3
except ModuleNotFoundError:  # pragma: no cover - optional dependency for S3 storage
    boto3 = None

from src.core.config import settings
from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger


class FileStorageService:
    """对象存储适配器"""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.logging.file_path).parent / "uploads"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.s3_config = settings.object_storage
        self.s3_client = None
        if boto3 is not None and self.s3_config.endpoint_url and self.s3_config.access_key and self.s3_config.secret_key:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.s3_config.endpoint_url,
                aws_access_key_id=self.s3_config.access_key,
                aws_secret_access_key=self.s3_config.secret_key,
                region_name=self.s3_config.region or "us-east-1",
                use_ssl=self.s3_config.use_ssl,
            )
        elif self.s3_config.endpoint_url and (boto3 is None):
            logger.warning(
                "S3-compatible storage configured but boto3 is not installed; falling back to local storage. "
                "Install boto3 to enable object storage uploads."
            )

    def _make_object_key(self, folder: str, file_name: str) -> str:
        safe_name = os.path.basename(file_name)
        stem, ext = os.path.splitext(safe_name)
        digest = hashlib.sha1(f"{datetime.now(timezone.utc).isoformat()}:{safe_name}".encode("utf-8")).hexdigest()[:12]
        unique_name = f"{stem}-{digest}{ext}"
        prefix = self.s3_config.prefix.strip("/")
        folder_prefix = folder.strip("/")
        if prefix and folder_prefix:
            return f"{prefix}/{folder_prefix}/{unique_name}"
        if prefix:
            return f"{prefix}/{unique_name}"
        if folder_prefix:
            return f"{folder_prefix}/{unique_name}"
        return unique_name

    def _build_public_url(self, key: str) -> str:
        if self.s3_config.public_url:
            return urllib.parse.urljoin(self.s3_config.public_url.rstrip("/") + "/", key.lstrip("/"))
        return f"/files/{key.lstrip('/')}"

    def save_upload(self, file: UploadFile, folder: str = "general", operator: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.s3_client is not None:
            return self._save_to_s3(file, folder=folder, operator=operator)
        return self._save_to_local(file, folder=folder)

    def _save_to_s3(self, file: UploadFile, folder: str = "general", operator: dict[str, Any] | None = None) -> dict[str, Any]:
        file_name = file.filename or "upload.bin"
        object_key = self._make_object_key(folder, file_name)
        file_bytes = file.file.read()
        self.s3_client.put_object(
            Bucket=self.s3_config.bucket,
            Key=object_key,
            Body=file_bytes,
            ContentType=file.content_type or "application/octet-stream",
        )

        logger.info(
            "Object storage upload success: bucket=%s key=%s operator_id=%s",
            self.s3_config.bucket,
            object_key,
            operator.get("operator_id") if operator else None,
        )

        file_url = self._build_public_url(object_key)
        return {
            "filename": os.path.basename(file_name),
            "key": object_key,
            "path": object_key,
            "url": file_url,
            "size": len(file_bytes),
            "storage": "s3",
        }

    def _save_to_local(self, file: UploadFile, folder: str = "general") -> dict[str, Any]:
        target_dir = self.base_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = file.filename or "upload.bin"
        safe_name = os.path.basename(file_name)
        file_path = target_dir / safe_name
        content = file.file.read()
        file_path.write_bytes(content)
        logger.info("Uploaded file saved: %s", file_path)
        return {
            "filename": safe_name,
            "path": str(file_path),
            "url": f"/files/{folder}/{safe_name}",
            "size": len(content),
            "storage": "local",
        }

    def get_url(self, relative_path: str) -> str:
        if self.s3_client is not None and self.s3_config.public_url:
            return urllib.parse.urljoin(self.s3_config.public_url.rstrip("/") + "/", relative_path.lstrip("/"))
        return f"/files/{relative_path.lstrip('/')}"

    def download_file(self, relative_path: str) -> FileResponse | StreamingResponse:
        """读取文件并构造下载响应。"""
        normalized_path = relative_path.strip("/")
        if not normalized_path or ".." in Path(normalized_path).parts:
            raise ValidationException(message="文件路径无效")

        filename = Path(normalized_path).name
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        content_disposition = f'attachment; filename="{filename}"'

        if self.s3_client is not None:
            try:
                response = self.s3_client.get_object(
                    Bucket=self.s3_config.bucket,
                    Key=normalized_path,
                )
            except Exception as exc:
                error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
                if error_code in {"NoSuchKey", "404", "NotFound"}:
                    raise NotFoundException(message="文件不存在") from exc
                raise

            return StreamingResponse(
                response["Body"].iter_chunks(),
                media_type=response.get("ContentType") or media_type,
                headers={"Content-Disposition": content_disposition},
            )

        file_path = (self.base_dir / normalized_path).resolve()
        try:
            file_path.relative_to(self.base_dir.resolve())
        except ValueError as exc:
            raise ValidationException(message="文件路径无效") from exc
        if not file_path.is_file():
            raise NotFoundException(message="文件不存在")

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
        )
