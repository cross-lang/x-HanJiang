#!/usr/bin/env python3
"""业务通知服务。"""

from src.infras.email import EmailProvider


class NotificationService:
    """业务通知服务。"""

    def __init__(self, email_provider: EmailProvider) -> None:
        self._email_provider = email_provider