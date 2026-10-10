"""用户通知渠道配置实体（合并原 user_notification_preferences）。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class UserNotificationConfigEntity(Base):
    """用户通知配置表（事件 × 渠道 二维配置）。

    一行 = 一个用户在某个事件下、某个渠道的推送配置：
    - enabled: 该 (事件, 渠道) 是否启用；
    - recipient: 该渠道的接收方（单值，email 为邮箱地址，dingtalk/feishu 为 webhook URL，station 为空串）。

    同一用户在同一事件下可配置多个渠道；同一用户同一渠道仅维护一份 recipient，
    后端在 upsert recipient 时会把该渠道下所有事件行的 recipient 同步刷新。
    """

    __tablename__ = "user_notification_configs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="事件类型（如 user.password_changed）")
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="通知渠道（station/email/dingtalk/feishu）"
    )
    recipient: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        default="",
        server_default=text("''"),
        comment="渠道接收方（单值；station 渠道为空串）",
    )
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
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("uk_user_event_channel", "user_id", "event_type", "channel", unique=True),
    )
