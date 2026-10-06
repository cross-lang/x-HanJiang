"""管理系统用户站内信实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class StationMessageEntity(Base):
    """管理系统用户站内信表（独立收件箱）。
    与系统通知投递明细解耦：本站只承载"用户收到了什么消息 + 是否已读"，
    投递实际情况由 notifications_delivery 记录；来源字段支撑前端跳转（如审批消息跳审批页）。
    """

    __tablename__ = "station_messages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="接收用户ID")
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="发送人用户ID（系统自动为空）")
    subject: Mapped[str] = mapped_column(String(200), nullable=False, comment="消息标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息正文")
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="消息来源（system_notice/station/alert/openapi_app）",
    )
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="事件类型（前端跳转依据）")
    is_read: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("0"), comment="是否已读"
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="阅读时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    __table_args__ = (
        Index("idx_station_user", "user_id"),
        Index("idx_station_user_read", "user_id", "is_read"),
        Index("idx_station_created_at", "created_at"),
    )
