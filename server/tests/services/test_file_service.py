#!/usr/bin/env python3
"""文件存储服务（FileStorageService）单元测试。

用 FakeStorageProvider（内存记录调用）+ FakeFileRepository（内存 dict）隔离：
    - save_bytes / save_upload：上传与元数据落库
    - list_files：列表字段映射（含上传人姓名拼接）
    - get_url / download_file：路径校验、远程 302 跳转、本地 FileResponse
    - delete_file：软删除与删除通知派发（含通知失败不阻断）
    - get_storage_stats：统计聚合
不连接真实 S3 / MySQL；审计写库由 conftest 统一降级为 no-op。
"""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from src.core.config import settings
from src.core.exceptions import NotFoundException, ValidationException
from src.infras.storage import LocalStorage, StorageProvider, UploadResult
from src.models.entities.file_entity import FileEntity
from src.services.file_service import FileStorageService


class FakeRemoteProvider(StorageProvider):
    """内存版远程存储替身：记录调用、按预置集合判断存在性。"""

    def __init__(self) -> None:
        self.uploaded: list[tuple[bytes, str, str]] = []
        self.download_calls: list[tuple[str, int]] = []
        self.exists_keys: set[str] = set()

    def upload_file(self, data: bytes, key: str, *, content_type: str = "application/octet-stream") -> UploadResult:
        self.uploaded.append((data, key, content_type))
        self.exists_keys.add(key)
        return UploadResult(
            key=key,
            url=f"https://cdn.example.com/{key}",
            size=len(data),
            storage="s3",
            content_type=content_type,
        )

    def get_download_url(self, key: str, *, expires: int = 3600) -> str:
        self.download_calls.append((key, expires))
        return f"https://cdn.example.com/{key}?expires={expires}"

    def delete_file(self, key: str) -> bool:
        self.exists_keys.discard(key)
        return True

    def file_exists(self, key: str) -> bool:
        return key in self.exists_keys

    def make_object_key(self, folder: str, filename: str) -> str:
        """确定性 key，便于断言。"""
        return f"{folder}/stored-{filename}"


class FakeFileRepository:
    """内存版文件仓库替身，记录写调用并按预设返回查询结果。"""

    def __init__(self) -> None:
        self.items: dict[int, FileEntity] = {}
        self._next_id = 1
        self.commits = 0
        # list_files 返回预设：(行列表[(FileEntity, UserLike|None)], 总数)
        self.list_rows: list[tuple[FileEntity, object | None]] = []
        self.list_total = 0
        self.list_calls: list[dict] = []
        self.stats_result: tuple[int, int, list] = (0, 0, [])

    def create(self, entity: FileEntity) -> FileEntity:
        entity.id = self._next_id
        self._next_id += 1
        self.items[entity.id] = entity
        return entity

    def commit(self) -> None:
        self.commits += 1

    def list_files(self, folder=None, uploaded_by=None, keyword=None, skip=0, limit=20):
        self.list_calls.append(
            {"folder": folder, "uploaded_by": uploaded_by, "keyword": keyword, "skip": skip, "limit": limit}
        )
        return self.list_rows, self.list_total

    def soft_delete(self, id: int) -> FileEntity | None:
        entity = self.items.get(id)
        if entity is None:
            return None
        entity.is_deleted = True
        return entity

    def get_storage_stats(self):
        return self.stats_result


def _make_service(provider=None, repo=None, dispatcher=None) -> FileStorageService:
    repo = repo or FakeFileRepository()
    provider = provider or FakeRemoteProvider()
    return FileStorageService(file_repository=repo, provider=provider, dispatcher=dispatcher)


class TestSaveUpload:
    """上传与元数据落库。"""

    def test_save_bytes_records_metadata(self):
        """显式 content_type 上传，返回结构与落库字段一致。"""
        repo = FakeFileRepository()
        provider = FakeRemoteProvider()
        svc = _make_service(provider=provider, repo=repo)

        result = svc.save_bytes(
            b"hello",
            filename="报告.pdf",
            folder="docs",
            content_type="application/pdf",
            operator={"operator_id": 5, "ip_address": "1.2.3.4"},
            uploaded_by_user=5,
            app_owner="app-1",
        )

        assert result["id"] == 1
        assert result["filename"] == "报告.pdf"
        assert result["key"] == "docs/stored-报告.pdf"
        assert result["size"] == 5
        assert result["storage"] == "s3"
        assert result["uploaded_by"] == 5
        assert result["uploaded_by_app"] == "app-1"
        assert repo.commits == 1

        entity = repo.items[1]
        assert entity.folder == "docs"
        assert entity.extension == "pdf"
        assert entity.mime_type == "application/pdf"
        assert entity.uploaded_by_app == "app-1"
        # provider 收到的 key 与字节一致
        assert provider.uploaded[0][1] == "docs/stored-报告.pdf"
        assert provider.uploaded[0][0] == b"hello"

    def test_save_bytes_guesses_mime_from_filename(self):
        """缺省 content_type 时按文件名猜测 MIME。"""
        svc = _make_service()
        result = svc.save_bytes(b"\x89PNG", filename="pic.png")
        assert result["content_type"] == "image/png"

    def test_save_upload_reads_uploadfile(self):
        """管理端 multipart 入口：读取 UploadFile 的 filename/content_type/字节。"""
        repo = FakeFileRepository()
        svc = _make_service(repo=repo)
        upload = UploadFile(filename="a.txt", file=BytesIO(b"abc"))

        result = svc.save_upload(upload, folder="general", operator={"operator_id": 9})

        assert result["size"] == 3
        assert result["filename"] == "a.txt"
        assert result["uploaded_by"] == 9


class TestListFiles:
    """列表字段映射。"""

    def test_list_files_maps_uploader(self):
        """有上传人时拼接『姓名（用户名）』，无上传人时回退为 uploaded_by 字符串。"""
        repo = FakeFileRepository()
        file_with_user = FileEntity(
            id=1,
            file_key="k1",
            original_name="a.png",
            stored_name="a.png",
            extension="png",
            mime_type="image/png",
            size_bytes=10,
            folder="general",
            storage_type="s3",
            url="u1",
            uploaded_by=7,
        )
        file_no_user = FileEntity(
            id=2,
            file_key="k2",
            original_name="b.bin",
            stored_name="b.bin",
            extension="bin",
            mime_type="application/octet-stream",
            size_bytes=20,
            folder="general",
            storage_type="local",
            url=None,
            uploaded_by=None,
        )
        repo.list_rows = [
            (file_with_user, SimpleNamespace(name="张三", username="zhangsan")),
            (file_no_user, None),
        ]
        repo.list_total = 2
        svc = _make_service(repo=repo)

        result = svc.list_files(folder="general", page=1, page_size=20)

        assert result["total"] == 2
        assert result["page"] == 1
        first, second = result["items"]
        assert first["uploader_display"] == "张三（zhangsan）"
        assert first["uploader_name"] == "张三"
        # 无上传人时回退为空串（uploaded_by 为 None）
        assert second["uploader_display"] == ""

    def test_list_files_passes_conditions_to_repo(self):
        """分页 skip 由 page/page_size 推导并下传仓库。"""
        repo = FakeFileRepository()
        svc = _make_service(repo=repo)
        svc.list_files(folder="avatars", uploaded_by=3, keyword="cat", page=2, page_size=10)
        call = repo.list_calls[0]
        assert call["folder"] == "avatars"
        assert call["uploaded_by"] == 3
        assert call["keyword"] == "cat"
        assert call["skip"] == 10
        assert call["limit"] == 10


class TestDownload:
    """下载与路径校验。"""

    def test_get_url_delegates_to_provider(self):
        provider = FakeRemoteProvider()
        svc = _make_service(provider=provider)
        assert svc.get_url("some/key.png") == "https://cdn.example.com/some/key.png?expires=3600"

    def test_download_rejects_path_traversal(self):
        """含 .. 的路径拒绝。"""
        svc = _make_service()
        with pytest.raises(ValidationException):
            svc.download_file("../etc/passwd")

    def test_download_rejects_empty_path(self):
        """全斜杠规范化后为空路径拒绝。"""
        svc = _make_service()
        with pytest.raises(ValidationException):
            svc.download_file("///")

    def test_download_remote_not_found(self):
        """远程存储文件不存在 → NotFound。"""
        provider = FakeRemoteProvider()
        svc = _make_service(provider=provider)
        with pytest.raises(NotFoundException):
            svc.download_file("missing.txt")

    def test_download_remote_redirect(self):
        """远程存储存在 → 302 重定向到带签名 URL。"""
        provider = FakeRemoteProvider()
        provider.upload_file(b"data", "docs/x.txt")
        svc = _make_service(provider=provider)

        resp = svc.download_file("docs/x.txt")
        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 302
        assert "docs/x.txt" in resp.headers["location"]
        # 远程下载要求 1 小时有效期
        assert provider.download_calls[0][1] == 3600

    def test_download_local_file_response(self, tmp_path, monkeypatch):
        """LocalStorage 分支：真实本地文件返回 FileResponse；缺失返回 404。"""
        provider = LocalStorage(base_dir=str(tmp_path))
        provider.upload_file(b"hello-content", "gen/hello.txt")
        # service 内 LocalStorage 分支读取 settings.storage.local.base_dir
        monkeypatch.setattr(settings.storage.local, "base_dir", str(tmp_path))
        svc = _make_service(provider=provider, repo=FakeFileRepository())

        resp = svc.download_file("gen/hello.txt")
        assert isinstance(resp, FileResponse)
        assert resp.media_type == "text/plain"

        with pytest.raises(NotFoundException):
            svc.download_file("gen/not-exist.txt")


class TestDeleteFile:
    """软删除与删除通知。"""

    def test_delete_not_found(self):
        repo = FakeFileRepository()
        svc = _make_service(repo=repo)
        with pytest.raises(NotFoundException):
            svc.delete_file(999)

    def test_delete_dispatches_notification_to_uploader(self):
        """软删除成功 → commit → 向上传者派发 FILE_DELETED。"""
        repo = FakeFileRepository()
        entity = FileEntity(
            id=1,
            file_key="k",
            original_name="a.png",
            stored_name="a.png",
            extension="png",
            mime_type="image/png",
            size_bytes=1,
            folder="general",
            storage_type="local",
            url=None,
            uploaded_by=7,
        )
        repo.items[1] = entity
        dispatcher = MagicMock()
        svc = _make_service(repo=repo, dispatcher=dispatcher)

        assert svc.delete_file(1, operator={"operator_name": "admin"}) is True
        assert repo.commits == 1
        assert repo.items[1].is_deleted is True
        dispatcher.dispatch_for_user.assert_called_once()
        kwargs = dispatcher.dispatch_for_user.call_args.kwargs
        assert kwargs["user_id"] == 7

    def test_delete_dispatcher_failure_swallowed(self):
        """通知派发异常不阻断删除主流程。"""
        repo = FakeFileRepository()
        repo.items[1] = FileEntity(
            id=1,
            file_key="k",
            original_name="a.png",
            stored_name="a.png",
            size_bytes=1,
            folder="general",
            storage_type="local",
            uploaded_by=7,
        )
        dispatcher = MagicMock()
        dispatcher.dispatch_for_user.side_effect = RuntimeError("boom")
        svc = _make_service(repo=repo, dispatcher=dispatcher)

        assert svc.delete_file(1) is True  # 不抛出


class TestStats:
    """存储统计聚合。"""

    def test_get_storage_stats(self):
        repo = FakeFileRepository()
        repo.stats_result = (1024, 3, [("general", 2, 512), ("avatars", 1, 512)])
        svc = _make_service(repo=repo)

        stats = svc.get_storage_stats()
        assert stats["total_size_bytes"] == 1024
        assert stats["total_count"] == 3
        assert stats["by_folder"] == [
            {"folder": "general", "count": 2, "size_bytes": 512},
            {"folder": "avatars", "count": 1, "size_bytes": 512},
        ]
