#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据库实体模型

本模块定义用户表的 ORM 映射，提供数据库层的实体定义。
与业务层的 Pydantic 模型（UserCreateRequest、UserResponse）分离，实现关注点分离。

Classes:
    UserEntity: 用户数据库实体
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.mysql import Base


class UserEntity(Base):
    """用户数据库实体模型。

    映射到数据库表 user，包含用户的核心信息字段。

    Attributes:
        id: 用户唯一标识（主键，自增）
        username: 用户名（唯一，3-50个字符）
        email: 邮箱地址
        name: 显示名称（1-100个字符）
        age: 年龄（可选，0-150）
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="用户唯一标识",
    )
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="用户名（唯一，3-50个字符）",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="邮箱地址",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称",
    )
    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="年龄（0-150）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="CURRENT_TIMESTAMP",
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="CURRENT_TIMESTAMP",
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    # 定义表级索引
    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_email", "email"),
    )

    def to_dict(self) -> dict:
        """将实体转换为字典。

        Returns:
            dict: 实体数据的字典表示
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "age": self.age,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
