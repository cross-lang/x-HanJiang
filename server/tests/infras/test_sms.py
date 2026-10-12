#!/usr/bin/env python3
"""
短信基础设施测试（src/infras/sms.py）

覆盖四种实现 / 分支：
    - MockSmsProvider：本地模拟，记录发送明细
    - TencentCloudSmsProvider：配置不完整跳过 / 成功 / 失败码 / 异常透传
    - AliyunSmsProvider：同上
    - get_sms_provider / get_cached_sms_provider：工厂按配置选择、未知厂商报错

云 SDK（tencentcloud / alibabacloud_*）属可选依赖，本测试通过向 sys.modules
注入桩模块模拟其导入与调用，不安装真实 SDK、不触网。
"""

import sys
from types import ModuleType, SimpleNamespace

import pytest
import src.infras.sms as sms_module
from src.infras.sms import (
    AliyunSmsProvider,
    MockSmsProvider,
    TencentCloudSmsProvider,
    get_cached_sms_provider,
    get_sms_provider,
)

# ── 云 SDK 桩模块安装 ─────────────────────────────────────────


def _make_module(name: str) -> ModuleType:
    return ModuleType(name)


def _install_tencent_fake(monkeypatch: pytest.MonkeyPatch, *, code: str = "Ok", raise_exc: Exception | None = None):
    """向 sys.modules 注入腾讯云短信 SDK 桩，返回调用捕获字典。"""
    captured: dict = {}

    cred_mod = _make_module("tencentcloud.common.credential")

    class FakeCredential:
        def __init__(self, sid, skey):
            captured["cred"] = (sid, skey)

    cred_mod.Credential = FakeCredential

    profile_mod = _make_module("tencentcloud.common.profile.client_profile")

    class FakeClientProfile:
        def __init__(self):
            self.httpProfile = None

    profile_mod.ClientProfile = FakeClientProfile

    http_mod = _make_module("tencentcloud.common.profile.http_profile")

    class FakeHttpProfile:
        def __init__(self):
            self.endpoint = ""

    http_mod.HttpProfile = FakeHttpProfile

    models_mod = _make_module("tencentcloud.sms.v20210111.models")

    class SendSmsMessageRequest:
        pass

    models_mod.SendSmsMessageRequest = SendSmsMessageRequest

    client_mod = _make_module("tencentcloud.sms.v20210111.sms_client")

    class FakeSmsClient:
        def __init__(self, cred, region, profile):
            captured["region"] = region

        def SendSmsMessage(self, req):  # noqa: N802 - 对齐腾讯云 SDK 方法名
            captured["req"] = req
            if raise_exc is not None:
                raise raise_exc
            return SimpleNamespace(SendStatusSet=[SimpleNamespace(Code=code)])

    client_mod.SmsClient = FakeSmsClient

    common_mod = _make_module("tencentcloud.common")
    common_mod.credential = cred_mod
    pkg_mod = _make_module("tencentcloud")
    sms_pkg_mod = _make_module("tencentcloud.sms")
    v2021_mod = _make_module("tencentcloud.sms.v20210111")
    v2021_mod.models = models_mod
    v2021_mod.sms_client = client_mod
    profile_pkg = _make_module("tencentcloud.common.profile")
    profile_pkg.client_profile = profile_mod
    profile_pkg.http_profile = http_mod

    for name, mod in {
        "tencentcloud": pkg_mod,
        "tencentcloud.common": common_mod,
        "tencentcloud.common.credential": cred_mod,
        "tencentcloud.common.profile": profile_pkg,
        "tencentcloud.common.profile.client_profile": profile_mod,
        "tencentcloud.common.profile.http_profile": http_mod,
        "tencentcloud.sms": sms_pkg_mod,
        "tencentcloud.sms.v20210111": v2021_mod,
        "tencentcloud.sms.v20210111.models": models_mod,
        "tencentcloud.sms.v20210111.sms_client": client_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return captured


def _install_aliyun_fake(monkeypatch: pytest.MonkeyPatch, *, code: str = "OK", raise_exc: Exception | None = None):
    """向 sys.modules 注入阿里云短信 SDK 桩，返回调用捕获字典。"""
    captured: dict = {}

    config_mod = _make_module("alibabacloud_tea_openapi.models")

    class FakeConfig:
        def __init__(self, **kw):
            captured["config"] = kw

    config_mod.Config = FakeConfig

    models_mod = _make_module("alibabacloud_dysmsapi20170525.models")

    class SendSmsRequest:
        def __init__(self, **kw):
            captured["req"] = kw

    models_mod.SendSmsRequest = SendSmsRequest

    client_mod = _make_module("alibabacloud_dysmsapi20170525.client")

    class FakeClient:
        def __init__(self, config):
            captured["client"] = config

        def send_sms(self, req):
            if raise_exc is not None:
                raise raise_exc
            return SimpleNamespace(body=SimpleNamespace(code=code))

    client_mod.Client = FakeClient

    dysms_pkg = _make_module("alibabacloud_dysmsapi20170525")
    dysms_pkg.models = models_mod
    dysms_pkg.client = client_mod
    tea_pkg = _make_module("alibabacloud_tea_openapi")
    tea_pkg.models = config_mod

    for name, mod in {
        "alibabacloud_dysmsapi20170525": dysms_pkg,
        "alibabacloud_dysmsapi20170525.models": models_mod,
        "alibabacloud_dysmsapi20170525.client": client_mod,
        "alibabacloud_tea_openapi": tea_pkg,
        "alibabacloud_tea_openapi.models": config_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return captured


# ── Mock 实现 ────────────────────────────────────────────────


class TestMockSmsProvider:
    def test_send_records_and_returns_true(self) -> None:
        provider = MockSmsProvider()
        assert provider.send_sms("13800138000", "TPL", {"code": "654321"}, sign_name="签名") is True
        records = provider.sent_records
        assert len(records) == 1
        assert records[0]["phone"] == "13800138000"
        assert records[0]["code"] == "654321"
        assert provider.last_code() == "654321"

    def test_last_code_empty_when_no_records(self) -> None:
        assert MockSmsProvider().last_code() == ""


# ── 腾讯云实现 ────────────────────────────────────────────────


class TestTencentSmsProvider:
    def test_incomplete_config_skips_without_sdk(self, monkeypatch) -> None:
        """凭据为空 → 直接返回 False，不导入 SDK（不安装 SDK 也能跑）。"""
        provider = TencentCloudSmsProvider(secret_id="", secret_key="", sdk_app_id="")
        assert provider.send_sms("13800138000", "TPL") is False

    def test_success_path(self, monkeypatch) -> None:
        captured = _install_tencent_fake(monkeypatch, code="Ok")
        provider = TencentCloudSmsProvider(
            secret_id="id", secret_key="key", sdk_app_id="sdk-app", region="ap-guangzhou", sign_name="全局签名"
        )
        assert provider.send_sms("13800138000", "TPL1", {"code": "123456"}, sign_name="局部签名") is True

        req = captured["req"]
        assert req.PhoneNumberSet == ["+8613800138000"]
        assert req.SmsSdkAppId == "sdk-app"
        assert req.SignName == "局部签名"  # 发送时显式签名优先
        assert req.TemplateId == "TPL1"
        assert "123456" in req.TemplateParamSet  # 模板变量 JSON

    def test_failure_code_returns_false(self, monkeypatch) -> None:
        _install_tencent_fake(monkeypatch, code="OtherErr")
        provider = TencentCloudSmsProvider(secret_id="id", secret_key="key", sdk_app_id="app")
        assert provider.send_sms("13800138000", "TPL") is False

    def test_exception_is_reraised(self, monkeypatch) -> None:
        _install_tencent_fake(monkeypatch, raise_exc=RuntimeError("网络异常"))
        provider = TencentCloudSmsProvider(secret_id="id", secret_key="key", sdk_app_id="app")
        with pytest.raises(RuntimeError, match="网络异常"):
            provider.send_sms("13800138000", "TPL")


# ── 阿里云实现 ────────────────────────────────────────────────


class TestAliyunSmsProvider:
    def test_incomplete_config_skips_without_sdk(self) -> None:
        provider = AliyunSmsProvider(access_key_id="", access_key_secret="")
        assert provider.send_sms("13800138000", "TPL") is False

    def test_success_path(self, monkeypatch) -> None:
        captured = _install_aliyun_fake(monkeypatch, code="OK")
        provider = AliyunSmsProvider(
            access_key_id="id", access_key_secret="secret", endpoint="dysmsapi.aliyuncs.com", sign_name="全局签名"
        )
        assert provider.send_sms("13800138000", "TPL1", {"code": "123456"}) is True

        req = captured["req"]
        assert req["phone_numbers"] == "13800138000"
        assert req["sign_name"] == "全局签名"
        assert req["template_code"] == "TPL1"
        assert "123456" in req["template_param"]

    def test_failure_code_returns_false(self, monkeypatch) -> None:
        _install_aliyun_fake(monkeypatch, code="isv.BUSINESS_LIMIT_CONTROL")
        provider = AliyunSmsProvider(access_key_id="id", access_key_secret="secret")
        assert provider.send_sms("13800138000", "TPL") is False

    def test_exception_is_reraised(self, monkeypatch) -> None:
        _install_aliyun_fake(monkeypatch, raise_exc=RuntimeError("网络异常"))
        provider = AliyunSmsProvider(access_key_id="id", access_key_secret="secret")
        with pytest.raises(RuntimeError, match="网络异常"):
            provider.send_sms("13800138000", "TPL")


# ── 工厂函数 ─────────────────────────────────────────────────


class TestSmsProviderFactory:
    @pytest.fixture(autouse=True)
    def _reset_cache(self, monkeypatch) -> None:
        """每个用例前后都清空模块级单例，避免污染其它测试。"""
        monkeypatch.setattr(sms_module, "_sms_provider", None)
        yield
        monkeypatch.setattr(sms_module, "_sms_provider", None)

    def _set_provider(self, monkeypatch, value: str) -> None:
        monkeypatch.setattr(sms_module.settings.sms, "provider", value)

    def test_mock_provider(self, monkeypatch) -> None:
        self._set_provider(monkeypatch, "mock")
        assert isinstance(get_sms_provider(), MockSmsProvider)

    def test_tencent_provider(self, monkeypatch) -> None:
        self._set_provider(monkeypatch, "tencent")
        provider = get_sms_provider()
        assert isinstance(provider, TencentCloudSmsProvider)

    def test_aliyun_provider(self, monkeypatch) -> None:
        self._set_provider(monkeypatch, "aliyun")
        assert isinstance(get_sms_provider(), AliyunSmsProvider)

    @pytest.mark.parametrize("disabled", ["", "none", "disabled"])
    def test_disabled_returns_none(self, monkeypatch, disabled: str) -> None:
        self._set_provider(monkeypatch, disabled)
        assert get_sms_provider() is None

    def test_unknown_provider_raises(self, monkeypatch) -> None:
        self._set_provider(monkeypatch, "carrier-pigeon")
        with pytest.raises(ValueError, match="不支持的短信服务商"):
            get_sms_provider()

    def test_cached_provider_is_singleton(self, monkeypatch) -> None:
        self._set_provider(monkeypatch, "mock")
        first = get_cached_sms_provider()
        second = get_cached_sms_provider()
        assert first is second
