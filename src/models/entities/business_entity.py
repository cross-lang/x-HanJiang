"""业务数据实体模型（任务、会话）。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class TaskEntity(Base):
    """任务表实体。"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    task_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="任务编号"
    )
    task_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="任务名称"
    )
    agent_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="执行Agent ID"
    )
    workspace_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="工作空间ID"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", comment="状态"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        onupdate=datetime.utcnow,
        comment="更新时间",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )

    __table_args__ = (
        Index("idx_tenant_id", "tenant_id"),
        Index("idx_agent_id", "agent_id"),
        Index("idx_workspace_id", "workspace_id"),
    )


class ConversationEntity(Base):
    """会话表实体。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    workspace_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="工作空间ID"
    )
    title: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="会话标题"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active", comment="状态"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_tenant_id", "tenant_id"),
        Index("idx_user_id", "user_id"),
        Index("idx_workspace_id", "workspace_id"),
    )


class ConversationMessageEntity(Base):
    """会话消息表实体。"""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="会话ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="消息角色"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=True, server_default="0", comment="消耗Token数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )

    __table_args__ = (
        Index("idx_conversation_id", "conversation_id"),
    )
