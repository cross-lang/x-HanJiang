"""系统级通知渠道配置实体。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class SystemNotificationConfigEntity(Base):
    """系统级通知渠道配置表。
    存全局通知渠道配置，如钉钉告警群webhook、飞书告警群webhook。
    和用户级配置的区别：这是全局共用的，不是某个用户的。
    """

    __tablename__ = "system_notification_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, comment="渠道（dingtalk/feishu/email）"
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="渠道配置对象，如webhook地址、密钥等")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"), comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="更新时间",
    )
