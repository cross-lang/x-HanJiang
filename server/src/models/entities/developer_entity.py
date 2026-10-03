"""开放平台开发者（门户账号）数据实体。

与管理系统 UserEntity 平行、分表：
- UserEntity      → users 表，管理系统账号（管理员），JWT 鉴权；
- DeveloperEntity → developers 表，开放平台门户账号（注册开发者），JWT 鉴权（get_current_developer）。

开发者通过门户自助注册、创建应用；应用归属用 owner_type/owner_id 区分
（developer → developers.id；admin → 管理系统 users.id，见 openapi_apps 表）。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class DeveloperEntity(Base):
    """开放平台开发者账号表。"""

    __tablename__ = "developers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户名（全局唯一）")
    email: Mapped[str] = mapped_column(String(100), nullable=False, comment="邮箱（全局唯一）")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希（bcrypt）")
    name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="", comment="姓名/昵称")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, server_default="", comment="手机号")
    # ── 开发者认证（预留：认证流程后续完善，字段先行）────────
    certification_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="认证类型：personal 个人认证 / enterprise 企业认证"
    )
    certification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="none",
        comment="认证状态：none 未认证 / pending 审批中 / approved 已认证 / rejected 已驳回",
    )
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="企业名称（企业认证）")
    credential_no: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="证件号（身份证/统一社会信用代码）"
    )
    # ── 账号状态 ──────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="enabled",
        comment="状态：enabled 启用 / disabled 禁用",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后登录时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="更新时间",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="软删除时间")
    __table_args__ = (
        Index("uk_developer_username", "username", unique=True),
        Index("uk_developer_email", "email", unique=True),
    )
