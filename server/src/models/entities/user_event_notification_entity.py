"""用户事件通知订阅实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class UserEventNotificationEntity(Base):
    """用户事件通知订阅表（事件 × 渠道配置的映射关系）。

    一行 = 用户把某份渠道配置（user_notification_configs.id）订阅到某个事件：
    - 行存在表示该 (渠道配置, 事件) 组合启用推送；
    - 行不存在表示未订阅，该事件不经该渠道推送。

    实际发送需同时满足：订阅行存在 + 渠道配置 enabled + recipient 非空。
    """

    __tablename__ = "user_event_notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    config_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user_notification_configs.id", ondelete="CASCADE"),
        nullable=False,
        comment="渠道配置ID（user_notification_configs.id）",
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="事件类型（如 user.password_changed）")
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
        Index("idx_config_id", "config_id"),
        Index("idx_event_type", "event_type"),
        Index("uk_config_event", "config_id", "event_type", unique=True),
    )
