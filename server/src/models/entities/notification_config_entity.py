"""用户通知渠道配置实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class UserNotificationConfigEntity(Base):
    """用户通知渠道配置表（渠道级，与事件解耦）。

    一行 = 一个用户在某个渠道的一份接收方配置：
    - recipient: 该渠道的接收方（单值，email 为邮箱地址，dingtalk/feishu 为 webhook URL，station 为空串）；
    - enabled: 该渠道是否启用推送（渠道级总开关）。

    事件维度的订阅关系由 user_event_notifications 表维护
    （一行 = 把某渠道配置订阅到某事件），本表不再含 event_type 字段。
    """

    __tablename__ = "user_notification_configs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
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
        Index("uk_user_channel", "user_id", "channel", unique=True),
    )
