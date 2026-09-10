"""租户配置数据实体模型（SSO、安全策略、品牌定制）。"""

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
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class SsoConfigEntity(Base):
    """SSO单点登录配置表实体。"""

    __tablename__ = "sso_configs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="是否启用"
    )
    protocol: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="oidc", comment="SSO协议"
    )
    issuer_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Issuer URL"
    )
    client_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Client ID"
    )
    client_secret: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Client Secret(加密)"
    )
    discovery_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Discovery URL(OIDC)"
    )
    idp_metadata_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="IdP Metadata URL(SAML)"
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Entity ID(SAML)"
    )
    callback_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="回调地址"
    )
    connection_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="disconnected", comment="连接状态"
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后测试时间"
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
        Index("uk_tenant_id", "tenant_id", unique=True),
    )


class SecurityPolicyEntity(Base):
    """安全策略表实体。"""

    __tablename__ = "security_policies"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    password_min_length: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="8", comment="密码最小长度"
    )
    login_fail_lock_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="5", comment="登录失败锁定阈值(次)"
    )
    session_timeout_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="30", comment="会话超时(分钟)"
    )
    ip_whitelist: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="IP白名单(CIDR逗号分隔)"
    )
    agent_api_rate_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100", comment="Agent API速率限制(次/分)"
    )
    approval_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100", comment="操作审批阈值(记录数)"
    )
    circuit_breaker_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="1", comment="是否启用熔断"
    )
    circuit_breaker_fail_rate: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="30", comment="熔断失败率阈值(%)"
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
        Index("uk_tenant_id", "tenant_id", unique=True),
    )


class BrandingEntity(Base):
    """品牌定制表实体。"""

    __tablename__ = "brandings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="租户ID(NULL=平台级)"
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="tenant", comment="作用域"
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="显示名称"
    )
    brand_color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, server_default="#0066FF", comment="品牌色(HEX)"
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="LOGO URL"
    )
    favicon_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Favicon URL"
    )
    welcome_message: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="登录欢迎语"
    )
    override_platform: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="是否覆盖平台品牌"
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
    )
