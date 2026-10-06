"""业务审计日志实体模型。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class AuditLogEntity(Base):
    """业务审计日志表实体。"""

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="审计日志ID")
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="实体类型")
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="实体ID")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="操作者ID")
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更前数据")
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更后数据")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="操作IP")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
