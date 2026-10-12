#!/usr/bin/env python3
"""
登录会话管理模块测试（src/core/session.py）

会话管理以 Redis 为"是否登录"的真实判据，本测试用 Fake 缓存提供者替身，
不连接真实 Redis，覆盖：
    - 正常写入 / 读取 / 删除登录态
    - 缓存不可用（未安装 / Redis 未配置）时的降级分支
    - 缓存抛异常时仅告警、不阻断业务
"""

from types import SimpleNamespace

import src.core.session as session_module


class FakeCache:
    """内存版缓存提供者替身，记录每次调用以便断言。"""

    def __init__(self, value: str | None = None, blow_up: bool = False) -> None:
        self._value = value
        self._blow_up = blow_up
        self.set_calls: list[tuple] = []
        self.deleted: list[str] = []

    def get(self, key: str) -> str | None:
        if self._blow_up:
            raise RuntimeError("redis down")
        return self._value

    def set(self, key: str, value: object, ttl: int = 300) -> None:
        if self._blow_up:
            raise RuntimeError("redis down")
        self.set_calls.append((key, value, ttl))

    def delete(self, key: str) -> None:
        if self._blow_up:
            raise RuntimeError("redis down")
        self.deleted.append(key)


def _patch_redis_enabled(monkeypatch, fake: FakeCache) -> None:
    """让会话模块认为缓存可用且已配置 Redis，并注入 Fake 提供者。"""
    monkeypatch.setattr(session_module, "_HAS_CACHE", True)
    monkeypatch.setattr(session_module, "get_cached_cache_provider", lambda: fake)
    monkeypatch.setattr(
        session_module, "settings", SimpleNamespace(redis=SimpleNamespace(url="redis://localhost:6379/0"))
    )


def _patch_redis_disabled(monkeypatch, *, has_cache: bool = True) -> None:
    """让会话模块走降级分支（Redis 未配置），并确保误触真连接时立即暴露。"""
    monkeypatch.setattr(session_module, "_HAS_CACHE", has_cache)

    def _boom() -> None:
        raise AssertionError("降级分支不应访问缓存提供者")

    monkeypatch.setattr(session_module, "get_cached_cache_provider", _boom)
    monkeypatch.setattr(session_module, "settings", SimpleNamespace(redis=SimpleNamespace(url="")))


class TestSetLoginStatus:
    """写入登录态。"""

    def test_writes_token_with_ttl(self, monkeypatch) -> None:
        """正常路径：以 login:<id> 为键写入令牌与 TTL。"""
        fake = FakeCache()
        _patch_redis_enabled(monkeypatch, fake)
        session_module.set_login_status(user_id=42, token="access-token-xyz", ttl_seconds=3600)
        assert fake.set_calls == [("login:42", "access-token-xyz", 3600)]

    def test_skips_when_cache_unavailable(self, monkeypatch) -> None:
        """未安装缓存依赖时直接返回，不触碰提供者。"""
        _patch_redis_disabled(monkeypatch, has_cache=False)
        session_module.set_login_status(1, "tok", 60)  # 不应抛异常

    def test_skips_when_redis_url_empty(self, monkeypatch) -> None:
        """Redis 未配置（url 为空）时直接返回。"""
        _patch_redis_disabled(monkeypatch)
        session_module.set_login_status(1, "tok", 60)

    def test_swallows_provider_error(self, monkeypatch) -> None:
        """写入失败仅告警，不向上抛异常（不能阻断登录）。"""
        fake = FakeCache(blow_up=True)
        _patch_redis_enabled(monkeypatch, fake)
        session_module.set_login_status(1, "tok", 60)


class TestGetLoginStatus:
    """读取登录态。"""

    def test_returns_stored_token(self, monkeypatch) -> None:
        """命中缓存时返回令牌，键名正确。"""
        seen: list[str] = []

        class RecordingCache(FakeCache):
            def get(self, key: str) -> str | None:
                seen.append(key)
                return "stored-token"

        fake = RecordingCache()
        _patch_redis_enabled(monkeypatch, fake)
        assert session_module.get_login_status(7) == "stored-token"
        assert seen == ["login:7"]

    def test_returns_none_when_cache_unavailable(self, monkeypatch) -> None:
        """未安装缓存依赖时返回 None（放行）。"""
        _patch_redis_disabled(monkeypatch, has_cache=False)
        assert session_module.get_login_status(7) is None

    def test_returns_none_when_redis_url_empty(self, monkeypatch) -> None:
        """Redis 未配置时返回 None。"""
        _patch_redis_disabled(monkeypatch)
        assert session_module.get_login_status(7) is None

    def test_returns_none_on_provider_error(self, monkeypatch) -> None:
        """读取异常时降级为 None，不抛异常。"""
        fake = FakeCache(blow_up=True)
        _patch_redis_enabled(monkeypatch, fake)
        assert session_module.get_login_status(7) is None


class TestIsLoggedIn:
    """登录态判断。"""

    def test_logged_in_when_token_present(self, monkeypatch) -> None:
        """存在令牌 → 已登录。"""
        _patch_redis_enabled(monkeypatch, FakeCache(value="tok"))
        assert session_module.is_logged_in(9) is True

    def test_not_logged_in_when_token_absent(self, monkeypatch) -> None:
        """无令牌（已登出）→ 未登录。"""
        _patch_redis_enabled(monkeypatch, FakeCache(value=None))
        assert session_module.is_logged_in(9) is False

    def test_degrade_pass_through_when_no_redis(self, monkeypatch) -> None:
        """Redis 不可用时降级放行（返回 True），不阻断鉴权。"""
        _patch_redis_disabled(monkeypatch)
        assert session_module.is_logged_in(9) is True


class TestClearLoginStatus:
    """登出删除登录态。"""

    def test_deletes_key(self, monkeypatch) -> None:
        """正常路径：删除 login:<id> 键。"""
        fake = FakeCache()
        _patch_redis_enabled(monkeypatch, fake)
        session_module.clear_login_status(3)
        assert fake.deleted == ["login:3"]

    def test_skips_when_cache_unavailable(self, monkeypatch) -> None:
        """缓存不可用时直接返回。"""
        _patch_redis_disabled(monkeypatch, has_cache=False)
        session_module.clear_login_status(3)

    def test_swallows_delete_error(self, monkeypatch) -> None:
        """删除失败仅告警，不抛异常。"""
        fake = FakeCache(blow_up=True)
        _patch_redis_enabled(monkeypatch, fake)
        session_module.clear_login_status(3)
