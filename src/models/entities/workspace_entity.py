"""工作空间与模型数据实体模型。"""

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


class TenantModelEntity(Base):
    """租户模型配置表实体（tenant_models）。"""

    __tablename__ = "tenant_models"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="", comment="模型供应商(具体标识,如 glm-5.2)"
    )
    provider_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="openai",
        comment="模型提供商类型",
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="模型名称"
    )
    api_base: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="", comment="API基础地址"
    )
    api_key: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="", comment="API密钥"
    )
    token_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="模型Token配额(每月)"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="4096", comment="单次最大输出Token数"
    )
    max_temperature: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="10", comment="最大温度参数(0-20,实际值=该值/10)"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="是否默认模型(同租户仅一个)"
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
        Index("idx_tenant_id", "tenant_id"),
    )


class WorkspaceEntity(Base):
    """工作空间表实体。"""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    workspace_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="空间名称"
    )
    workspace_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="空间编码"
    )
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="空间描述"
    )
    user_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100", comment="用户数配额"
    )
    agent_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="10", comment="Agent配额"
    )
    token_budget: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="Token预算(每天)"
    )
    default_model_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="默认模型ID(关联tenant_models.id)"
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
        Index("idx_tenant_id", "tenant_id"),
        Index("idx_default_model_id", "default_model_id"),
    )
