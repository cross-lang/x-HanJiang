"""用户通知偏好实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class UserNotificationPreferenceEntity(Base):
    """用户通知偏好表。

    存储用户对各事件的通知渠道偏好，如：
    - 密码修改事件 → 站内信 ✅、邮件 ✅、钉钉 ❌
    - 文件上传事件 → 站内信 ✅、邮件 ❌、钉钉 ❌
    """

    __tablename__ = "user_notification_preferences"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID"
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="事件类型，如 user.password_changed"
    )
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="通知渠道（station/email/dingtalk/feishu）"
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
        Index("uk_user_event_channel", "user_id", "event_type", "channel", unique=True),
    )
