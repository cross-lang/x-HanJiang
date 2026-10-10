"""开放平台应用申请（审批批次）数据实体。

openapi_app_registrations 表按"批次"记录开发者对同一应用提交的每次申请：
- 创建申请（registration_type=create）：应用记录随申请一并创建，审批通过后应用 approved 置 True；
- 修改申请（registration_type=update）：基本信息 / scope 调整统一走该类型，
  申请内容以快照形式记录在表中，审批通过后由管理系统将快照落地到 openapi_apps 表。

应用表 openapi_apps 不再承载审批字段，应用级授权状态仅保留 approved 标记；
每次申请的审批人、审批意见、审批时间均记录在本表，支持多批次区分与追溯。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class OpenApiAppRegistrationEntity(Base):
    """开放平台应用申请表（每次创建/修改申请为一条批次记录）。"""

    __tablename__ = "openapi_app_registrations"
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="申请ID（批次号，内部主键）"
    )
    registration_code: Mapped[str] = mapped_column(
        String(6), nullable=False, comment="申请码：6位数字，对外展示用（管理后台/门户端均展示申请码而非申请ID）"
    )
    app_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="应用ID（openapi_apps.id）")
    registration_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="申请类型：create 创建申请 / update 修改申请"
    )
    # ── 申请内容快照（审批通过后整体落地到应用表）────────
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="申请的应用名")
    description: Mapped[str] = mapped_column(String(255), nullable=False, comment="申请的应用描述")
    scopes: Mapped[str] = mapped_column(
        String(500), nullable=False, server_default="", comment="申请的权限范围，逗号分隔"
    )
    auth_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="plain", comment="申请的鉴权模式：plain/hmac/both"
    )
    apply_reason: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="开发者填写的申请说明/用途")
    # ── 审批结果 ────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", comment="审批状态：pending/approved/rejected"
    )
    approved_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="审批人用户ID（管理系统 users.id），未审批为 NULL"
    )
    approval_note: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="审批意见/驳回原因")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审批时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.current_timestamp(),
    )
    __table_args__ = (
        Index("idx_reg_app", "app_id"),
        Index("idx_reg_status", "status"),
        UniqueConstraint("registration_code", name="uq_reg_code"),
    )
