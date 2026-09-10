"""日志与监控数据实体模型。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class AuditLogEntity(Base):
    """审计日志表实体。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="租户ID"
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="操作用户ID"
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作动作")
    resource_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="资源类型"
    )
    resource_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="资源ID"
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="操作详情")
    scope: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="授权范围"
    )
    result: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="操作结果"
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="IP地址"
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="User-Agent"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )

    __table_args__ = (
        Index("idx_tenant_id", "tenant_id"),
        Index("idx_user_id", "user_id"),
    )


class ActivityLogEntity(Base):
    """活动日志表实体。"""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="租户ID"
    )
    activity_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="活动类型"
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="活动描述"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )

    __table_args__ = (
        Index("idx_tenant_id", "tenant_id"),
    )


class QuotaUsageEntity(Base):
    """配额使用表实体。"""

    __tablename__ = "quota_usages"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    quota_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="配额类型"
    )
    used_value: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", comment="已用值"
    )
    total_value: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", comment="总量值"
    )
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="monthly", comment="统计周期"
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


class QuotaAdjustmentRequestEntity(Base):
    """配额调整申请表实体。"""

    __tablename__ = "quota_adjustment_requests"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="租户ID"
    )
    quota_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="配额类型"
    )
    target_value: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="目标值"
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="申请理由")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", comment="审批状态"
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


class TokenUsageRecordEntity(Base):
    """租户Token用量明细表实体。"""

    __tablename__ = "token_usage_records"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属租户ID"
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="用户ID（平台级调用为NULL）"
    )
    agent_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="Agent资源ID"
    )
    model: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="模型名称"
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="输入token数"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="输出token数"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="总token数"
    )
    period_month: Mapped[str] = mapped_column(
        CHAR(7), nullable=False, comment="月度聚合键(YYYY-MM)"
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
        Index("idx_tenant_period", "tenant_id", "period_month"),
        Index("idx_user_id", "user_id"),
    )


class LoginLogEntity(Base):
    """登录日志表实体。"""

    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="租户ID"
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="用户ID"
    )
    login_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="password", comment="登录方式"
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="IP地址"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="登录结果"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="CURRENT_TIMESTAMP", comment="创建时间"
    )

    __table_args__ = (
        Index("idx_tenant_id", "tenant_id"),
        Index("idx_user_id", "user_id"),
    )
