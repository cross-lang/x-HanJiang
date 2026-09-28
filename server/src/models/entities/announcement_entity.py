"""公告实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class AnnouncementEntity(Base):
    """公告表。
    记录首页板块/横幅展示的公告，支持创建、修改、删除、发布、下架，
    并设置有效期（start_at ~ end_at），正文支持 Markdown 与富文本两种格式。
    """

    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="公告标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="公告正文")
    content_type: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="markdown", comment="正文格式（markdown/richtext）"
    )
    position: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="board", comment="展示位置（board/banner）"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="draft", comment="发布状态（draft/published/unpublished）"
    )
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="生效开始时间")
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="生效结束时间")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="展示排序（越小越靠前）"
    )
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="操作人用户ID")
    operator_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="操作人用户名")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发布时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="更新时间")
    __table_args__ = (
        Index("idx_announcement_status", "status"),
        Index("idx_announcement_position", "position"),
        Index("idx_announcement_period", "start_at", "end_at"),
    )
