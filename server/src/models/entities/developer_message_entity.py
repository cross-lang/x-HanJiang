"""开放平台开发者站内信数据实体。

与管理系统用户站内信分表：
- 管理系统用户站内信 → station_messages 表；
- 开放平台开发者站内信 → developer_messages 表（developer_id 直接外键语义）。

遵循"不同平台用户身份分表"的既定原则（developers 与 users 分表同源），
开发者站内信独立建表，字段按 web/open_portal 前端 OpenMessage 约定
（title / content / category / read / created_at）设计，服务层落库时映射。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class DeveloperMessageEntity(Base):
    """开放平台开发者站内信表。"""

    __tablename__ = "developer_messages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    developer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="收件开发者 ID（developers.id）")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="消息标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息正文")
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="system",
        comment="消息类型：system 系统消息 / audit 审批结果 / notify 业务通知",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="unread",
        comment="阅读状态：unread 未读 / read 已读",
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="软删除时间")
    __table_args__ = (Index("idx_dev_msg_developer", "developer_id"),)
