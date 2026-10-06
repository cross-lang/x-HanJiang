"""系统通知（广播通知）实体。"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class SystemNotificationEntity(Base):
    """系统通知表。

    记录管理员面向全体用户发布的广播通知（普通通知 / 系统维护），
    支持发布后撤回，用于通知管理页面的发布记录、撤回与查看。
    投递明细（谁、什么渠道、何时送达）独立存放于 system_notice_delivery 表。

    维护参数（maintenance_time/duration_hours/reason）、强推渠道、受众快照、
    强推成功数等可变扩展信息统一存放于 metadata_json JSON 列。
    """

    __tablename__ = "system_notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知正文")
    notice_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="通知类型（notice/maintenance）")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="published",
        comment="发布状态（published/withdrawn）",
    )
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="操作人用户ID")
    operator_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="操作人用户名")
    client_request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, comment="发布幂等键（同一请求重复提交返回首次结果）"
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "扩展元数据：维护参数 maintenance_time/duration_hours/reason、"
            "强推渠道 push_channels、受众快照 target_type/target_roles/target_user_ids、"
            "强推成功数 sent_count"
        ),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发布时间")
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="撤回时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="最近更新时间（撤回/重新发布时刷新）",
    )
    __table_args__ = (
        Index("idx_notice_type", "notice_type"),
        Index("idx_notice_status", "status"),
        Index("idx_notice_created_at", "created_at"),
    )
