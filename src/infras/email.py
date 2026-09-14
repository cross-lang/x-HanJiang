#!/usr/bin/env python3
"""SMTP 邮件发送基础设施。"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.config import settings
from src.core.logger import logger


class EmailService:
    """通用 SMTP 邮件发送服务。"""

    def __init__(self) -> None:
        self._smtp_host: str = settings.smtp.host
        self._smtp_port: int = settings.smtp.port
        self._smtp_username: str = settings.smtp.username
        self._smtp_password: str = settings.smtp.password
        self._use_tls: bool = settings.smtp.use_tls
        self._from_name: str = settings.smtp.from_name
        self._from_address: str = settings.smtp.from_address or settings.smtp.username

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
