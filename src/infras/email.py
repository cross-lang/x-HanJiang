#!/usr/bin/env python3
"""SMTP 邮件发送基础设施。"""

from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.config import settings
from src.core.logger import logger


# ============================================================
# 抽象基类
# ============================================================

class EmailProvider(ABC):
    """邮件发送抽象接口。

    所有邮件后端必须实现此接口。业务层仅依赖此抽象，
    切换邮件实现只需修改配置，无需改动任何业务代码。
    """

    @abstractmethod
    def send_email(
        self,
        to_address: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """发送邮件。

        Args:
            to_address: 收件人地址
            subject: 邮件主题
            html_content: HTML 正文
            text_content: 纯文本正文（可选）

        Returns:
            bool: 发送是否成功
        """


# ============================================================
# SMTP 实现
# ============================================================

class SmtpEmailProvider(EmailProvider):
    """SMTP 邮件发送实现。"""

    def __init__(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        from_name: str = "",
        from_address: str = "",
    ) -> None:
        self._smtp_host = host
        self._smtp_port = port
        self._smtp_username = username
        self._smtp_password = password
        self._use_tls = use_tls
        self._from_name = from_name
        self._from_address = from_address or username

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """创建 SMTP 连接，支持 465 隐式 SSL 和其他端口 STARTTLS。"""
        if self._smtp_port == 465:
            smtp = smtplib.SMTP_SSL(self._smtp_host, self._smtp_port, timeout=30)
        else:
            smtp = smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=30)
            if self._use_tls:
                smtp.starttls()
        if self._smtp_username and self._smtp_password:
            smtp.login(self._smtp_username, self._smtp_password)
        return smtp

    def send_email(
        self,
        to_address: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """发送通用 HTML/纯文本邮件。"""
        if not self._smtp_host or not self._from_address:
            logger.warning("SMTP 配置不完整，跳过邮件发送")
            return False

        message = MIMEMultipart("alternative")
        message["From"] = f"{self._from_name} <{self._from_address}>"
        message["To"] = to_address
        message["Subject"] = subject
        if text_content:
            message.attach(MIMEText(text_content, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            smtp = self._create_smtp_connection()
            try:
                smtp.sendmail(self._from_address, to_address, message.as_string())
                logger.info(f"邮件发送成功: to={to_address}, subject={subject}")
                return True
            finally:
                smtp.quit()
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(f"SMTP 认证失败: {exc}")
            raise ValueError("邮件服务认证失败，请检查 SMTP 配置") from exc
        except smtplib.SMTPException as exc:
            logger.error(f"SMTP 发送失败: {exc}")
            raise Exception(f"邮件发送失败: {exc}") from exc
        except Exception as exc:
            logger.error(f"邮件发送异常: {exc}")
            raise


# ============================================================
# 工厂函数
# ============================================================

def get_email_provider() -> EmailProvider:
    """根据配置创建邮件提供者实例。"""
    cfg = settings.smtp
    return SmtpEmailProvider(
        host=cfg.host,
        port=cfg.port,
        username=cfg.username,
        password=cfg.password,
        use_tls=cfg.use_tls,
        from_name=cfg.from_name,
        from_address=cfg.from_address,
    )


# 模块级缓存实例
_email_provider: EmailProvider | None = None


def get_cached_email_provider() -> EmailProvider:
    """获取缓存的邮件提供者（应用级别单例）。"""
    global _email_provider
    if _email_provider is None:
        _email_provider = get_email_provider()
    return _email_provider


__all__ = [
    "EmailProvider",
    "SmtpEmailProvider",
    "get_email_provider",
    "get_cached_email_provider",
]
