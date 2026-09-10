"""平台级数据实体模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class PlatformConfigEntity(Base):
    """平台配置表实体。"""

    __tablename__ = "platform_config"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    config_group: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="配置组: brand/smtp/storage/global"
    )
    config_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="配置键名"
    )
    config_value: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="配置值"
    )
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="配置说明"
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
        Index("uk_config_key", "config_key", unique=True),
    )


class TenantEntity(Base):
    """租户表实体。"""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="租户编码"
    )
    tenant_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="租户名称"
    )
    isolation_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="shared", comment="隔离模式"
    )
    user_quota: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="1000", comment="用户数配额"
    )
    agent_quota: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="50", comment="Agent配额"
    )
    token_quota_monthly: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="10000000", comment="月度Token配额"
    )
    admin_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="租户管理员用户ID(关联users.id)"
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
        Index("uk_tenant_code", "tenant_code", unique=True),
    )


class LicenseEntity(Base):
    """License许可证表实体。"""

    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    license_key: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="License密钥"
    )
    license_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="授权类型"
    )
    license_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="计费模式"
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="有效期开始"
    )
    valid_to: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="有效期结束"
    )
    user_seats_total: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户总席位"
    )
    agent_seats_total: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Agent总席位"
    )
    token_quota_monthly: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="月度Token总配额"
    )
    industry_modules: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="行业模块"
    )
    node_binding: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="节点绑定信息"
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
        Index("uk_license_key", "license_key", unique=True),
    )


class TenantLicenseAllocationEntity(Base):
    """租户License分配表实体。"""

    __tablename__ = "tenant_license_allocations"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    license_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="License ID"
    )
    user_seats: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="分配用户席位"
    )
    agent_seats: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="分配Agent席位"
    )
    token_quota_monthly: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="分配月度Token配额"
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
        Index("idx_license_id", "license_id"),
    )
