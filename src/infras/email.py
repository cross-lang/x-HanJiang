#!/usr/bin/env python3
"""
邮件发送基础设施

本模块封装 SMTP 协议邮件发送功能，作为基础设施层供业务服务调用。
主要用于发送密码重置邮件、通知邮件等。

Classes:
    EmailService: 邮件发送服务实现
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.core.config import settings
from src.core.logger import logger


class EmailService:
    """邮件发送服务实现。

    使用 SMTP 协议发送邮件，支持 TLS 加密。
    配置从 settings.smtp 读取。
    """

    def __init__(self) -> None:
        """初始化邮件服务。"""
        self._smtp_host: str = settings.smtp.host
        self._smtp_port: int = settings.smtp.port
        self._smtp_username: str = settings.smtp.username
        self._smtp_password: str = settings.smtp.password
        self._use_tls: bool = settings.smtp.use_tls
        self._from_name: str = settings.smtp.from_name
        self._from_address: str = settings.smtp.from_address or settings.smtp.username

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """创建 SMTP 连接。

        端口 465 使用隐式 SSL（SMTP_SSL），其他端口使用明文 + 可选 STARTTLS。

        Returns:
            smtplib.SMTP: SMTP 连接对象

        Raises:
            Exception: 连接失败时抛出
        """
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
        """发送邮件。

        Args:
            to_address: 收件人邮箱地址
            subject: 邮件主题
            html_content: HTML 格式邮件内容
            text_content: 纯文本格式邮件内容（可选，作为 HTML 的降级方案）

        Returns:
            bool: 发送成功返回 True，失败返回 False

        Raises:
            ValueError: 邮箱配置不完整时抛出
            Exception: 发送失败时抛出
        """
        if not self._smtp_host or not self._from_address:
            logger.warning("SMTP 配置不完整，跳过邮件发送")
            return False

        # 创建邮件对象
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self._from_name} <{self._from_address}>"
        msg["To"] = to_address
        msg["Subject"] = subject

        # 添加纯文本内容（降级方案）
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))

        # 添加 HTML 内容
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            smtp = self._create_smtp_connection()
            try:
                smtp.sendmail(self._from_address, to_address, msg.as_string())
                logger.info(f"邮件发送成功: to={to_address}, subject={subject}")
                return True
            finally:
                smtp.quit()
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP 认证失败: {e}")
            raise ValueError("邮件服务认证失败，请检查 SMTP 配置") from e
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 发送失败: {e}")
            raise Exception(f"邮件发送失败: {e}") from e
        except Exception as e:
            logger.error(f"邮件发送异常: {e}")
            raise

    def send_password_reset_email(
        self,
        to_address: str,
        username: str,
        reset_token: str,
        frontend_url: str | None = None,
    ) -> bool:
        """发送密码重置邮件。

        Args:
            to_address: 收件人邮箱地址
            username: 用户名
            reset_token: 重置令牌
            frontend_url: 前端重置密码页面 URL（可选，覆盖配置）

        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        base_url = frontend_url or settings.password_reset.frontend_url
        reset_link = f"{base_url}/reset-password?token={reset_token}"

        subject = "【HanJiang】密码重置请求"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #1a73e8;
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    margin-bottom: 30px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #1a73e8;
                    color: #ffffff !important;
                    text-decoration: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-weight: 500;
                    margin: 20px 0;
                }}
                .button:hover {{
                    background-color: #1557b0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eeeeee;
                    font-size: 12px;
                    color: #666666;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffc107;
                    border-radius: 4px;
                    padding: 12px;
                    margin: 20px 0;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 密码重置</h1>
                </div>
                <div class="content">
                    <p>尊敬的 <strong>{username}</strong>，您好！</p>
                    <p>我们收到了您的密码重置请求。请点击下方按钮重置您的密码：</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">重置密码</a>
                    </p>
                    <p>或者复制以下链接到浏览器地址栏：</p>
                    <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 4px; font-size: 14px;">
                        {reset_link}
                    </p>
                    <div class="warning">
                        <strong>⚠️ 安全提示：</strong>
                        <ul style="margin: 5px 0;">
                            <li>此链接有效期为 {settings.password_reset.token_expire_minutes} 分钟</li>
                            <li>如果您没有请求重置密码，请忽略此邮件</li>
                            <li>请勿将此链接分享给他人</li>
                        </ul>
                    </div>
                </div>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿直接回复。</p>
                    <p>© 2024 HanJiang. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        【HanJiang】密码重置请求

        尊敬的 {username}，您好！

        我们收到了您的密码重置请求。请访问以下链接重置您的密码：

        {reset_link}

        安全提示：
        - 此链接有效期为 {settings.password_reset.token_expire_minutes} 分钟
        - 如果您没有请求重置密码，请忽略此邮件
        - 请勿将此链接分享给他人

        此邮件由系统自动发送，请勿直接回复。
        © 2024 HanJiang. All rights reserved.
        """

        return self.send_email(
            to_address=to_address,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
