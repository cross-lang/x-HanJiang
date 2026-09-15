#!/usr/bin/env python3
"""业务通知服务。"""

from src.core.config import settings
from src.infras.email import EmailProvider


class NotificationService:
    """业务通知服务。"""

    def __init__(self, email_provider: EmailProvider) -> None:
        self._email_provider = email_provider

    def send_password_reset_email(
        self,
        to_address: str,
        username: str,
        reset_token: str,
        frontend_url: str | None = None,
    ) -> bool:
        """发送密码重置邮件。"""
        base_url = frontend_url or settings.password_reset.frontend_url
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        expire_minutes = settings.password_reset.token_expire_minutes

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333;
                    max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background: #fff; border-radius: 8px; padding: 30px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, .1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #1a73e8; }}
                .button {{ display: inline-block; background: #1a73e8; color: #fff !important;
                    text-decoration: none; padding: 12px 24px; border-radius: 6px;
                    font-weight: 500; margin: 20px 0; }}
                .link {{ word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 4px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;
                    padding: 12px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;
                    font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>密码重置</h1></div>
                <p>尊敬的 <strong>{username}</strong>，您好！</p>
                <p>我们收到了您的密码重置请求。请点击下方按钮重置您的密码：</p>
                <p style="text-align: center;"><a href="{reset_link}" class="button">重置密码</a></p>
                <p>或者复制以下链接到浏览器地址栏：</p>
                <p class="link">{reset_link}</p>
                <div class="warning">
                    <strong>安全提示：</strong>
                    <ul>
                        <li>此链接有效期为 {expire_minutes} 分钟</li>
                        <li>如果您没有请求重置密码，请忽略此邮件</li>
                        <li>请勿将此链接分享给他人</li>
                    </ul>
                </div>
                <div class="footer"><p>此邮件由系统自动发送，请勿直接回复。</p></div>
            </div>
        </body>
        </html>
        """
        text_content = f"""【HanJiang】密码重置请求

尊敬的 {username}，您好！

请访问以下链接重置您的密码：
{reset_link}

此链接有效期为 {expire_minutes} 分钟。如果您没有请求重置密码，请忽略此邮件。
"""

        return self._email_provider.send_email(
            to_address=to_address,
            subject="【HanJiang】密码重置请求",
            html_content=html_content,
            text_content=text_content,
        )
