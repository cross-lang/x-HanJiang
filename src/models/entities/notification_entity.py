"""通知记录实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class NotificationRecordEntity(Base):
    """通知发送记录表。

    记录每一次通知的发送状态，用于审计、重试和查询。
    """

    __tablename__ = "notification_records"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="事件类型"
    )
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="发送渠道"
    )
    recipient: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="接收人"
    )
    subject: Mapped[str] = mapped_column(
        String(512), nullable=False, server_default="", comment="通知主题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="渲染后正文"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending", comment="发送状态"
    )
    retry_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0"), comment="已重试次数"
    )
    max_retries: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("3"), comment="最大重试次数"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="扩展元数据 JSON"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="发送时间"
    )

    __table_args__ = (
        Index("idx_event_type", "event_type"),
        Index("idx_channel", "channel"),
        Index("idx_status", "status"),
        Index("idx_status_retry", "status", "retry_count"),
        Index("idx_created_at", "created_at"),
    )
