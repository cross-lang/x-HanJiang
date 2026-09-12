"""用户与权限数据实体模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.mysql import Base


class UserEntity(Base):
    """用户表实体。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="用户名"
    )
    email: Mapped[str] = mapped_column(String(100), nullable=False, comment="邮箱")
    name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="姓名"
    )
    age: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="年龄"
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="密码哈希"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="头像URL"
    )
    role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="主角色ID"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="active",
        comment="状态",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后登录时间"
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="最后登录IP"
    )
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="软删除时间"
    )

    __table_args__ = (
        Index("uk_email", "email", unique=True),
        Index("idx_role_id", "role_id"),
    )


class RoleEntity(Base):
    """角色表实体。"""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    role_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色名称"
    )
    role_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色编码"
    )
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="角色描述"
    )
    role_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="custom",
        comment="类型",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="enabled",
        comment="状态",
    )
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="软删除时间"
    )


class PermissionEntity(Base):
    """权限表实体。"""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    perm_code: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="权限编码"
    )
    perm_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="权限名称"
    )
    module: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="所属模块"
    )
    operation: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="操作类型"
    )
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="权限说明"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="排序序号"
    )

    __table_args__ = (
        Index("uk_perm_code", "perm_code", unique=True),
        Index("idx_module", "module"),
    )


class RolePermissionEntity(Base):
    """角色权限关联表实体。"""

    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="角色ID")
    permission_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="权限ID"
    )

    __table_args__ = (
        Index("idx_role_id", "role_id"),
        Index("idx_permission_id", "permission_id"),
    )
