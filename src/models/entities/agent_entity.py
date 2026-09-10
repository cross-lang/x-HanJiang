"""智能体与模型数据实体模型。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class ModelConfigEntity(Base):
    """模型配置表实体。"""

    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="模型名称"
    )
    model_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="模型编码"
    )
    provider: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="模型提供商"
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

    __table_args__ = (
        Index("uk_model_code", "model_code", unique=True),
    )


class SkillEntity(Base):
    """技能表(Skill仓库)实体。"""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID(强绑定)"
    )
    skill_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="技能名称"
    )
    skill_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="技能编码(租户内唯一)"
    )
    skill_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="技能类型"
    )
    domain: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="领域分类"
    )
    version: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="版本号(如 v1.0)"
    )
    skill_md: Mapped[str | None] = mapped_column(
        LONGTEXT, nullable=True, comment="SKILL.md 内容"
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="all", comment="下发范围"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="enabled", comment="状态"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="技能描述"
    )
    call_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", comment="调用次数"
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
        Index("uk_skill_tenant_code", "tenant_id", "skill_code", unique=True),
        Index("idx_skills_tenant_id", "tenant_id"),
        Index("idx_skills_domain", "domain"),
        Index("idx_skills_status", "status"),
    )


class McpServerEntity(Base):
    """MCP Server 注册表实体。"""

    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID(强绑定)"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="MCP Server 名称"
    )
    endpoint_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="端点 URL"
    )
    auth_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="none", comment="认证方式"
    )
    credential: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="凭证(API Key/Token/OAuth配置,加密存储)"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="描述"
    )
    tool_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="工具数"
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="all", comment="下发范围"
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
        Index("idx_mcp_servers_tenant_id", "tenant_id"),
        Index("idx_mcp_servers_status", "status"),
        Index("idx_mcp_servers_auth_type", "auth_type"),
    )


class AgentEntity(Base):
    """Agent 模板库实体。"""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID(强绑定)"
    )
    agent_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Agent 名称"
    )
    domain: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="领域分类"
    )
    system_prompt: Mapped[str | None] = mapped_column(
        LONGTEXT, nullable=True, comment="System Prompt"
    )
    default_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="默认模型"
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="all", comment="下发范围"
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
        Index("idx_agents_tenant_id", "tenant_id"),
        Index("idx_agents_domain", "domain"),
        Index("idx_agents_status", "status"),
    )
