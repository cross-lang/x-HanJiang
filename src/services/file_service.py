#!/usr/bin/env python3
"""文件存储和管理服务。

通过 StorageProvider 抽象层实现，业务代码不关心底层存储是本地还是七牛。
切换存储实现只需修改配置文件，无需改动任何业务代码。

配置示例（config.yaml）：
    storage:
      provider: "local"          # local | s3
      local:
        base_dir: "static"
      s3:
        endpoint_url: "https://s3.cn-south-1.qiniucs.com"
        access_key: "ak"
        secret_key: "sk"
        bucket: "my-bucket"
        region: "cn-south-1"
        prefix: "uploads"
"""

from __future__ import annotations

import mimetypes
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from src.core.exceptions import NotFoundException, ValidationException
from src.core.logger import logger
from src.infras.storage import StorageProvider, get_cached_storage_provider


class FileStorageService:
    """文件存储服务（业务层）。

    对外暴露统一的上传/下载接口，内部委托给 StorageProvider。
    API 层和其他服务只依赖此门面，不直接接触 Provider 实现。
    """

    def __init__(self, provider: StorageProvider | None = None) -> None:
        self._provider = provider or get_cached_storage_provider()
        logger.info(f"FileStorageService initialized with provider: {type(self._provider).__name__}")

    def save_upload(
        self,
        file: UploadFile,
        folder: str = "general",
        operator: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """保存上传文件。

        Args:
            file: FastAPI UploadFile 对象
            folder: 存储目录前缀（如 "avatars"、"documents"）
            operator: 操作人上下文（用于审计日志）

        Returns:
            dict: 包含 filename, key, url, size, storage 字段
        """
        file_name = file.filename or "upload.bin"
        content_type = file.content_type or "application/octet-stream"
        key = self._provider.make_object_key(folder, file_name)
        data = file.file.read()

        result = self._provider.upload_file(data, key, content_type=content_type)

        logger.info(
            f"File uploaded: key={result.key} storage={result.storage} "
            f"size={result.size} operator_id={operator.get('operator_id') if operator else None}"
        )

        return {
            "filename": file_name,
            "key": result.key,
            "path": result.key,
            "url": result.url,
            "size": result.size,
            "storage": result.storage,
            "content_type": result.content_type,
        }

    def get_url(self, key: str) -> str:
        """获取文件访问 URL。

        Args:
            key: 存储路径键（如上传时返回的 key/path）

        Returns:
            str: 可访问的 URL
        """
        return self._provider.get_download_url(key)

    def download_file(self, file_path: str) -> FileResponse | RedirectResponse | StreamingResponse:
        """读取文件并构造下载响应。

        根据存储后端返回不同类型的响应：
        - 本地存储：直接返回 FileResponse
        - 七牛等云存储：返回 302 重定向到签名 URL

        Args:
            file_path: 文件相对路径（上传接口返回的 key 或 path）

        Returns:
            FileResponse | RedirectResponse | StreamingResponse
        """
        normalized_path = file_path.strip("/")
        if not normalized_path or ".." in Path(normalized_path).parts:
            raise ValidationException(message="文件路径无效")

        filename = Path(normalized_path).name
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # 云存储后端 → 重定向到签名 URL
        provider_name = type(self._provider).__name__
        if provider_name != "LocalStorage":
            if not self._provider.file_exists(normalized_path):
                raise NotFoundException(message="文件不存在")
            download_url = self._provider.get_download_url(normalized_path, expires=3600)
            return RedirectResponse(url=download_url, status_code=302)

        # 本地存储后端 → 直接返回文件
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

    def delete_file(self, key: str) -> bool:
        """删除文件。

        Args:
            key: 存储路径键

        Returns:
            bool: 删除是否成功
        """
        result = self._provider.delete_file(key)
        if result:
            logger.info(f"File deleted: key={key}")
        else:
            logger.warning(f"File delete failed or not found: key={key}")
        return result
