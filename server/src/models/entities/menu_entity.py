#!/usr/bin/env python3
"""菜单表实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class MenuEntity(Base):
    """菜单表实体（树形结构）。"""

    __tablename__ = "menus"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    parent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="父菜单ID，0=根菜单")
    title: Mapped[str] = mapped_column(String(50), nullable=False, comment="菜单名称")
    path: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="路由路径")
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="图标名")
    perm_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="关联权限码，为空表示所有人可见")
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="排序")
    type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="menu", comment="类型：目录/菜单")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="enabled", comment="状态")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
