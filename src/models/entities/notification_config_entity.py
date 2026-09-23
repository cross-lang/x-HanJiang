"""用户通知渠道配置实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class UserNotificationConfigEntity(Base):
    """用户通知渠道配置表。

    存储用户在各通知渠道的接收人标识，支持启用/禁用。
    """

    __tablename__ = "user_notification_configs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="通知渠道（email/sms/dingtalk/feishu）"
    )
    recipient: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="渠道接收人标识"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("1"), comment="是否启用"
    )
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

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("uk_user_channel", "user_id", "channel", unique=True),
    )
