"""日志数据实体模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class LoginLogEntity(Base):
    """登录日志表实体。"""

    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="用户ID"
    )
    login_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="password",
        comment="登录方式",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="IP地址"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="登录结果"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )

    __table_args__ = (
        Index("idx_user_id", "user_id"),
    )
