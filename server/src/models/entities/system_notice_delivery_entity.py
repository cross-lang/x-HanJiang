"""系统通知投递明细实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class SystemNoticeDeliveryEntity(Base):
    """系统通知投递明细表。
    记录每次通知投递的实际情况（发给谁、什么渠道、成没成、何时送达），
    同时承担失败重试队列（pending/failed + retry_count/max_retries）。
    来源不限于系统通知（system_notification_id 可为空），
    告警/审批/手动站内信等投递也统一记录，用 source 区分来源。
    """

    __tablename__ = "system_notice_delivery"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    system_notification_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="关联系统通知ID（非系统通知来源为空）"
    )
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="通知来源（system_notice/station/alert/openapi_app）"
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="事件类型")
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="目标用户ID（渠道级投递如告警webhook为空）"
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, comment="发送渠道")
    recipient: Mapped[str] = mapped_column(String(256), nullable=False, comment="接收人（发送时实际地址快照）")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending", comment="发送状态")
    retry_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"), comment="已重试次数")
    max_retries: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("3"), comment="最大重试次数"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    receive_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="送达/接收时间")
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
        Index("idx_delivery_notification", "system_notification_id"),
        Index("idx_delivery_user", "user_id"),
        Index("idx_delivery_status_retry", "status", "retry_count"),
        Index("idx_delivery_created_at", "created_at"),
    )
