"""资源中心关联数据实体模型（下发与绑定关联表）。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class SkillUserRelationEntity(Base):
    """Skill-用户下发关联表实体。"""

    __tablename__ = "skill_user_relations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    skill_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="技能ID(关联skills.id)"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID(关联users.id)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="enabled", comment="状态"
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="软删除时间"
    )

    __table_args__ = (
        Index("uk_sur_skill_user", "skill_id", "user_id", unique=True),
        Index("idx_sur_tenant_id", "tenant_id"),
        Index("idx_sur_skill_id", "skill_id"),
        Index("idx_sur_user_id", "user_id"),
        Index("idx_sur_status", "status"),
    )


class McpServerUserRelationEntity(Base):
    """MCP Server-用户下发关联表实体。"""

    __tablename__ = "mcp_server_user_relations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    mcp_server_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="MCP Server ID(关联mcp_servers.id)"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID(关联users.id)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="enabled", comment="状态"
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="软删除时间"
    )

    __table_args__ = (
        Index("uk_msur_mcp_user", "mcp_server_id", "user_id", unique=True),
        Index("idx_msur_tenant_id", "tenant_id"),
        Index("idx_msur_mcp_server_id", "mcp_server_id"),
        Index("idx_msur_user_id", "user_id"),
        Index("idx_msur_status", "status"),
    )


class AgentUserRelationEntity(Base):
    """Agent-用户下发关联表实体。"""

    __tablename__ = "agent_user_relations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    agent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Agent ID(关联agents.id)"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID(关联users.id)"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="enabled", comment="状态"
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="软删除时间"
    )

    __table_args__ = (
        Index("uk_aur_agent_user", "agent_id", "user_id", unique=True),
        Index("idx_aur_tenant_id", "tenant_id"),
        Index("idx_aur_agent_id", "agent_id"),
        Index("idx_aur_user_id", "user_id"),
        Index("idx_aur_status", "status"),
    )


class AgentSkillEntity(Base):
    """Agent-Skill绑定关联表实体。"""

    __tablename__ = "agent_skills"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    agent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Agent ID(关联agents.id)"
    )
    skill_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="技能ID(关联skills.id)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )

    __table_args__ = (
        Index("uk_as_agent_skill", "agent_id", "skill_id", unique=True),
        Index("idx_as_tenant_id", "tenant_id"),
        Index("idx_as_agent_id", "agent_id"),
        Index("idx_as_skill_id", "skill_id"),
    )


class AgentMcpEntity(Base):
    """Agent-MCP Server绑定关联表实体。"""

    __tablename__ = "agent_mcps"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    agent_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Agent ID(关联agents.id)"
    )
    mcp_server_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="MCP Server ID(关联mcp_servers.id)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )

    __table_args__ = (
        Index("uk_am_agent_mcp", "agent_id", "mcp_server_id", unique=True),
        Index("idx_am_tenant_id", "tenant_id"),
        Index("idx_am_agent_id", "agent_id"),
        Index("idx_am_mcp_server_id", "mcp_server_id"),
    )
