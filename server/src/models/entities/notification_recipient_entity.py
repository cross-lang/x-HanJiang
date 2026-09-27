"""通知接收人实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class NotificationRecipientEntity(Base):
    """通知接收人表（一对多）。

    一个用户在每个渠道可以绑定多个接收人地址：
    - email: zhangsan@qq.com, zhangsan_work@qq.com
    - dingtalk: 群机器人webhook1, 群机器人webhook2
    - feishu: 飞书群ID1, 飞书群ID2

    user_id 为 NULL 表示系统级接收人（如告警群）。
    """

    __tablename__ = "user_notification_recipients"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="用户ID，NULL=系统级接收人"
    )
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="通知渠道（email/dingtalk/feishu）"
    )
    recipient: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="接收人地址（邮箱/钉钉群webhook/飞书群ID）"
    )
    label: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="备注标签，如'工作邮箱'、'运维群'"
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
        Index("idx_channel", "channel"),
    )
