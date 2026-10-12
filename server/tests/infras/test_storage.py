#!/usr/bin/env python3
"""
文件存储抽象层测试（src/infras/storage.py）

覆盖：
    - UploadResult 结构
    - StorageProvider.make_object_key 唯一键生成
    - LocalStorage：上传（bytes / 文件对象）、路径穿越防护、下载 URL、删除、存在判断
    - S3CompatibleStorage：上传、预签名 URL、删除成败、存在判断（boto3 通过 sys.modules 桩）
    - get_storage_provider 工厂：local / s3 凭据不全回退 local
    - 单例缓存

boto3 属可选依赖，本测试不安装真实 SDK、不触网。
"""

import io
import sys
from types import ModuleType

import pytest
import src.infras.storage as storage_module
from src.core.config import settings
from src.infras.storage import (
    LocalStorage,
    S3CompatibleStorage,
    UploadResult,
    get_cached_storage_provider,
    get_storage_provider,
)

# ── 基础结构与键生成 ─────────────────────────────────────────


class TestUploadResult:
    def test_to_dict(self) -> None:
        result = UploadResult(key="a/b.png", url="/files/a/b.png", size=10, storage="local", content_type="image/png")
        assert result.to_dict() == {
            "key": "a/b.png",
            "url": "/files/a/b.png",
            "size": 10,
            "storage": "local",
            "content_type": "image/png",
        }


class TestMakeObjectKey:
    def test_includes_folder_and_ext(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        key = storage.make_object_key("avatars", "cat.png")
        assert key.startswith("avatars/cat-")
        assert key.endswith(".png")

    def test_strips_path_components(self, tmp_path) -> None:
        """只取 basename，避免目录穿越注入。"""
        storage = LocalStorage(base_dir=str(tmp_path))
        key = storage.make_object_key("avatars", "/tmp/../../evil.png")
        assert ".." not in key
        assert key.startswith("avatars/evil-")

    def test_empty_folder_no_leading_slash(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        key = storage.make_object_key("", "x.png")
        assert not key.startswith("/")


# ── 本地存储 ─────────────────────────────────────────────────


class TestLocalStorage:
    def test_upload_bytes(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path / "statics"))
        data = b"hello"
        result = storage.upload_file(data, "avatars/u.png", content_type="image/png")
        assert result.size == len(data)
        assert result.storage == "local"
        assert result.url == "/files/avatars/u.png"
        # 文件确实落盘
        assert (tmp_path / "statics" / "avatars" / "u.png").read_bytes() == data

    def test_upload_file_like_object(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        result = storage.upload_file(io.BytesIO(b"binary"), "docs/a.txt")
        assert result.size == 6
        assert storage.file_exists("docs/a.txt") is True

    def test_path_traversal_rejected(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path / "statics"))
        with pytest.raises(ValueError, match="非法的存储路径"):
            storage.upload_file(b"x", "../escape.png")

    def test_download_url(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        assert storage.get_download_url("avatars/u.png") == "/files/avatars/u.png"

    def test_delete_existing_and_missing(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        storage.upload_file(b"x", "f.png")
        assert storage.delete_file("f.png") is True
        assert storage.delete_file("f.png") is False  # 已删除

    def test_delete_traversal_returns_false(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        assert storage.delete_file("../etc/passwd") is False

    def test_file_exists_traversal_returns_false(self, tmp_path) -> None:
        storage = LocalStorage(base_dir=str(tmp_path))
        assert storage.file_exists("../outside.png") is False


# ── S3 兼容存储（boto3 桩）───────────────────────────────────


def _install_boto3_fake(monkeypatch: pytest.MonkeyPatch, *, delete_raises: bool = False, head_raises: bool = False):
    """注入 boto3 / botocore 桩，返回 (captured, fake_client)。"""
    captured: dict = {}

    class FakeClientError(Exception):
        pass

    class _FakeExceptions:
        # 对齐 boto3 client.exceptions 命名空间
        ClientError = FakeClientError

    class FakeS3Client:
        def __init__(self, **kw):
            captured["init"] = kw

        def put_object(self, **kw):
            captured["put"] = kw
            return {}

        def generate_presigned_url(self, method, **kw):
            # boto3 关键字为 Params / ExpiresIn，此处原样透传
            params = kw.get("Params")
            captured["presign"] = (method, params, kw.get("ExpiresIn"))
            return f"https://signed.example/{params['Key']}"

        def delete_object(self, **kw):
            captured["delete"] = kw
            if delete_raises:
                raise RuntimeError("delete failed")
            return {}

        def head_object(self, **kw):
            captured["head"] = kw
            if head_raises:
                raise self.exceptions.ClientError({"Error": {"Code": "404"}}, "Not Found")
            return {}

        exceptions = _FakeExceptions

    fake = FakeS3Client()

    boto3_mod = ModuleType("boto3")

    def _client(service, **kw):
        assert service == "s3"
        captured["client_args"] = kw
        return fake

    boto3_mod.client = _client

    botocore_mod = ModuleType("botocore")
    config_mod = ModuleType("botocore.config")

    class FakeBotoConfig:
        def __init__(self, **kw):
            captured["boto_config"] = kw

    config_mod.Config = FakeBotoConfig
    botocore_mod.config = config_mod

    for name, mod in {
        "boto3": boto3_mod,
        "botocore": botocore_mod,
        "botocore.config": config_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return captured, fake


class TestS3CompatibleStorage:
    def _make(self, monkeypatch, *, public_url: str = "") -> tuple[dict, S3CompatibleStorage]:
        captured, _ = _install_boto3_fake(monkeypatch)
        storage = S3CompatibleStorage(
            endpoint_url="https://s3.example.com",
            access_key="ak",
            secret_key="sk",
            bucket="my-bucket",
            region="cn-south-1",
            prefix="uploads",
            public_url=public_url,
        )
        return captured, storage

    def test_upload_builds_full_key_and_url(self, monkeypatch) -> None:
        captured, storage = self._make(monkeypatch, public_url="https://cdn.example.com")
        result = storage.upload_file(b"data", "avatars/u.png", content_type="image/png")

        assert result.key == "uploads/avatars/u.png"  # prefix 拼接
        assert result.url == "https://cdn.example.com/uploads/avatars/u.png"
        assert result.size == 4
        assert result.storage == "s3"
        put = captured["put"]
        assert put["Bucket"] == "my-bucket"
        assert put["Key"] == "uploads/avatars/u.png"
        assert put["ContentType"] == "image/png"

    def test_public_url_defaults_to_qiniu_domain(self, monkeypatch) -> None:
        captured, storage = self._make(monkeypatch, public_url="")
        result = storage.upload_file(b"x", "f.png")
        assert result.url == "https://my-bucket.s3.cn-south-1.qiniucs.com/uploads/f.png"

    def test_presigned_download_url(self, monkeypatch) -> None:
        captured, storage = self._make(monkeypatch)
        url = storage.get_download_url("f.png", expires=600)
        assert "signed.example" in url
        assert captured["presign"][2] == 600

    def test_delete_success(self, monkeypatch) -> None:
        _, storage = self._make(monkeypatch)
        assert storage.delete_file("f.png") is True

    def test_delete_failure_returns_false(self, monkeypatch) -> None:
        _install_boto3_fake(monkeypatch, delete_raises=True)
        storage = S3CompatibleStorage(
            endpoint_url="https://s3.example.com",
            access_key="ak",
            secret_key="sk",
            bucket="b",
        )
        assert storage.delete_file("f.png") is False

    def test_file_exists_when_head_ok(self, monkeypatch) -> None:
        _, storage = self._make(monkeypatch)
        assert storage.file_exists("f.png") is True

    def test_file_exists_false_on_client_error(self, monkeypatch) -> None:
        _install_boto3_fake(monkeypatch, head_raises=True)
        storage = S3CompatibleStorage(
            endpoint_url="https://s3.example.com",
            access_key="ak",
            secret_key="sk",
            bucket="b",
        )
        assert storage.file_exists("f.png") is False


# ── 工厂函数 ─────────────────────────────────────────────────


class TestStorageFactory:
    @pytest.fixture(autouse=True)
    def _reset_cache(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setattr(storage_module, "_provider", None)
        # 用临时目录承载 local 实现，避免在项目目录创建 statics
        monkeypatch.setattr(settings.storage.local, "base_dir", str(tmp_path / "statics"))
        yield
        monkeypatch.setattr(storage_module, "_provider", None)

    def test_default_local_provider(self, monkeypatch) -> None:
        monkeypatch.setattr(settings.storage, "provider", "local")
        provider = get_storage_provider()
        assert isinstance(provider, LocalStorage)

    def test_s3_with_incomplete_credentials_falls_back_local(self, monkeypatch) -> None:
        """选择 s3 但凭据不全 → 回退本地存储。"""
        monkeypatch.setattr(settings.storage, "provider", "s3")
        monkeypatch.setattr(settings.storage.s3, "endpoint_url", "")
        provider = get_storage_provider()
        assert isinstance(provider, LocalStorage)

    def test_cached_provider_is_singleton(self, monkeypatch) -> None:
        monkeypatch.setattr(settings.storage, "provider", "local")
        assert get_cached_storage_provider() is get_cached_storage_provider()
