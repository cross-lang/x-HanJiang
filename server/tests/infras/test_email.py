#!/usr/bin/env python3
"""
SMTP 邮件发送专项测试（src/infras/email.py）

Mock smtplib（patch smtplib.SMTP / smtplib.SMTP_SSL 及连接对象），不触网，覆盖：
    - 端口 465 → SMTP_SSL 隐式 SSL 分支
    - 非 465 端口 + use_tls=True → SMTP + starttls()
    - 非 465 端口 + use_tls=False → 不调用 starttls
    - 有 username+password → login；无 → 跳过 login
    - host / from_address 不完整 → 返回 False 且不建立连接
    - 成功路径：sendmail 收到正确 from/to 与完整 MIME、返回 True、quit 被调用
    - SMTPAuthenticationError → ValueError；SMTPException → 通用 Exception
    - get_email_provider / get_cached_email_provider 工厂与单例
"""

import email
import smtplib

import pytest
import src.infras.email as email_module
from src.core.config import settings
from src.infras.email import (
    SmtpEmailProvider,
    get_cached_email_provider,
    get_email_provider,
)


class FakeSMTPConnection:
    """模拟 smtplib.SMTP / SMTP_SSL 连接对象，记录调用并可注入发送错误。"""

    instances: list["FakeSMTPConnection"] = []
    # 类级注入：sendmail 是否抛错（用例间用 monkeypatch 隔离）
    sendmail_error: Exception | None = None

    def __init__(self, host: str, port: int, timeout: int = 30) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.starttls_called = False
        self.login_called: tuple[str, str] | None = None
        self.sendmail_args: tuple | None = None
        self.quit_called = False
        FakeSMTPConnection.instances.append(self)

    def starttls(self) -> None:
        self.starttls_called = True

    def login(self, username: str, password: str) -> None:
        self.login_called = (username, password)

    def sendmail(self, from_addr: str, to_addrs: str, msg: str):
        self.sendmail_args = (from_addr, to_addrs, msg)
        if self.sendmail_error is not None:
            raise self.sendmail_error
        return {}

    def quit(self) -> None:
        self.quit_called = True


@pytest.fixture(autouse=True)
def _reset_fake_smtp(monkeypatch: pytest.MonkeyPatch):
    """每个用例重置连接实例列表、清空 sendmail 错误，并打桩 smtplib。"""
    FakeSMTPConnection.instances = []
    FakeSMTPConnection.sendmail_error = None
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTPConnection)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTPConnection)
    yield


def _make_provider(**kwargs) -> SmtpEmailProvider:
    """构造一个默认配置齐全的 Provider，用例可覆盖任意参数。"""
    defaults = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "noreply@example.com",
        "password": "secret",
        "use_tls": True,
        "from_name": "HanJiang",
        "from_address": "noreply@example.com",
    }
    defaults.update(kwargs)
    return SmtpEmailProvider(**defaults)


# ── 连接分支 ──────────────────────────────────────────────────


class TestConnectionBranches:
    def test_port_465_uses_smtp_ssl(self) -> None:
        """465 端口走 SMTP_SSL，不调用 starttls。"""
        provider = _make_provider(port=465, use_tls=False)
        assert provider.send_email("to@x.com", "主题", "<b>正文</b>") is True

        assert len(FakeSMTPConnection.instances) == 1
        conn = FakeSMTPConnection.instances[0]
        assert conn.port == 465
        assert conn.starttls_called is False  # 隐式 SSL，无需 starttls
        assert conn.quit_called is True

    def test_non_465_with_tls_uses_starttls(self) -> None:
        """非 465 + use_tls=True：普通 SMTP 且调用 starttls。"""
        provider = _make_provider(port=587, use_tls=True)
        provider.send_email("to@x.com", "主题", "<b>正文</b>")
        conn = FakeSMTPConnection.instances[0]
        assert conn.starttls_called is True

    def test_non_465_without_tls_skips_starttls(self) -> None:
        """非 465 + use_tls=False：不调用 starttls。"""
        provider = _make_provider(port=25, use_tls=False)
        provider.send_email("to@x.com", "主题", "<b>正文</b>")
        conn = FakeSMTPConnection.instances[0]
        assert conn.starttls_called is False

    def test_login_called_when_credentials_present(self) -> None:
        """配置了 username+password → login 被调用。"""
        provider = _make_provider(username="u", password="p")
        provider.send_email("to@x.com", "主题", "<b>正文</b>")
        assert FakeSMTPConnection.instances[0].login_called == ("u", "p")

    def test_login_skipped_when_no_credentials(self) -> None:
        """未配置凭据 → 不调用 login。"""
        provider = _make_provider(username="", password="")
        provider.send_email("to@x.com", "主题", "<b>正文</b>")
        assert FakeSMTPConnection.instances[0].login_called is None


# ── 配置不完整的跳过分支 ──────────────────────────────────────


class TestIncompleteConfig:
    def test_empty_host_returns_false_without_connecting(self) -> None:
        """host 为空 → 返回 False，且不建立任何连接。"""
        provider = _make_provider(host="")
        assert provider.send_email("to@x.com", "主题", "<b>正文</b>") is False
        assert FakeSMTPConnection.instances == []

    def test_empty_from_address_returns_false(self) -> None:
        """host 有值但 from_address / username 都为空 → 返回 False，不触网。"""
        provider = SmtpEmailProvider(host="smtp.example.com", port=465, username="", from_address="")
        assert provider.send_email("to@x.com", "主题", "<b>正文</b>") is False
        assert FakeSMTPConnection.instances == []

    def test_from_address_falls_back_to_username(self) -> None:
        """from_address 缺省时回退为 username，配置仍视为完整。"""
        provider = SmtpEmailProvider(host="smtp.example.com", port=465, username="noreply@example.com", password="p")
        assert provider.send_email("to@x.com", "主题", "<b>正文</b>") is True


# ── 成功路径的 MIME 内容 ──────────────────────────────────────


class TestSendPayload:
    def test_sendmail_receives_envelope_and_mime(self) -> None:
        """sendmail 信封发件人/收件人正确，消息为完整 MIME。"""
        provider = _make_provider(from_name="HanJiang", from_address="noreply@example.com")
        provider.send_email("to@x.com", "找回密码", "<b>点此重置</b>", text_content="点此重置")

        conn = FakeSMTPConnection.instances[0]
        from_addr, to_addr, raw_msg = conn.sendmail_args
        assert from_addr == "noreply@example.com"
        assert to_addr == "to@x.com"

        msg = email.message_from_string(raw_msg)
        # From 头带中文名编码
        assert "noreply@example.com" in msg["From"]
        assert msg["To"] == "to@x.com"
        # 中文 Subject 经 RFC2047 编码，解码后应为原文
        decoded_subject = str(email.header.make_header(email.header.decode_header(msg["Subject"])))
        assert decoded_subject == "找回密码"
        # 同时挂载 plain 与 html 两个 alternative 部分
        body = msg.get_payload()
        assert any(p.get_content_type() == "text/html" for p in body)
        assert any(p.get_content_type() == "text/plain" for p in body)


# ── 异常映射 ─────────────────────────────────────────────────


class TestErrorMapping:
    def test_auth_error_maps_to_value_error(self) -> None:
        """SMTPAuthenticationError → ValueError。"""
        FakeSMTPConnection.sendmail_error = smtplib.SMTPAuthenticationError(535, b"auth failed")
        provider = _make_provider()
        with pytest.raises(ValueError, match="邮件服务认证失败"):
            provider.send_email("to@x.com", "主题", "<b>正文</b>")

    def test_smtp_exception_maps_to_generic_exception(self) -> None:
        """SMTPException → 通用 Exception。"""
        FakeSMTPConnection.sendmail_error = smtplib.SMTPException("send failure")
        provider = _make_provider()
        with pytest.raises(Exception, match="邮件发送失败"):
            provider.send_email("to@x.com", "主题", "<b>正文</b>")

    def test_unexpected_exception_is_reraised(self) -> None:
        """非 SMTP 体系异常 → 记录后原样向上抛出。"""
        FakeSMTPConnection.sendmail_error = RuntimeError("意外断开")
        provider = _make_provider()
        with pytest.raises(RuntimeError, match="意外断开"):
            provider.send_email("to@x.com", "主题", "<b>正文</b>")


# ── 工厂函数 ─────────────────────────────────────────────────


class TestEmailFactory:
    @pytest.fixture(autouse=True)
    def _reset_cache(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(email_module, "_email_provider", None)
        yield
        monkeypatch.setattr(email_module, "_email_provider", None)

    def test_get_email_provider_builds_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """工厂按 settings.smtp 构造 Provider，参数透传。"""
        monkeypatch.setattr(settings.smtp, "host", "smtp.fromenv.com")
        monkeypatch.setattr(settings.smtp, "port", 465)
        monkeypatch.setattr(settings.smtp, "username", "env@x.com")
        monkeypatch.setattr(settings.smtp, "password", "env-pass")
        monkeypatch.setattr(settings.smtp, "use_tls", False)
        monkeypatch.setattr(settings.smtp, "from_name", "Env")
        monkeypatch.setattr(settings.smtp, "from_address", "env@x.com")

        provider = get_email_provider()
        assert isinstance(provider, SmtpEmailProvider)
        assert provider._smtp_host == "smtp.fromenv.com"
        assert provider._smtp_port == 465

    def test_cached_provider_is_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings.smtp, "host", "smtp.fromenv.com")
        first = get_cached_email_provider()
        second = get_cached_email_provider()
        assert first is second
