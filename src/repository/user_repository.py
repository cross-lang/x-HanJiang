#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据访问实现

本模块提供用户 Repository 的 SQLAlchemy 数据库实现，支持真实数据库存储。
使用 ORM 映射实现数据持久化，符合企业级应用标准。

Classes:
    UserRepository: 用户数据访问 SQLAlchemy 实现
"""

from typing import Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from src.models.user import UserResponse, UserCreateRequest, UserUpdateRequest
from src.models.entities.user_entity import UserEntity
from src.repository.base_repository import BaseRepository


class UserRepository(BaseRepository[UserResponse, int]):
    """用户数据访问 SQLAlchemy 实现。

    使用 SQLAlchemy ORM 进行数据库操作，支持连接池和事务管理。
    实现了 BaseRepository 定义的全部 CRUD 接口。

    Attributes:
        session: 数据库会话对象
    """

    def __init__(self, session: Session) -> None:
        """初始化用户仓库。

        Args:
            session: SQLAlchemy 数据库会话
        """
        self.session: Session = session

    def get_by_id(self, id: int) -> Optional[UserResponse]:
        """根据用户 ID 查询用户。

        Args:
            id: 用户唯一标识

        Returns:
            Optional[UserResponse]: 用户信息，不存在时返回 None
        """
        stmt = select(UserEntity).where(UserEntity.id == id)
        result = self.session.execute(stmt).scalar_one_or_none()

        if result is None:
            return None

        return UserResponse(**result.to_dict())

    def get_all(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """查询所有用户（分页）。

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            List[UserResponse]: 用户列表
        """
        stmt = select(UserEntity).offset(skip).limit(limit)
        results = self.session.execute(stmt).scalars().all()

        return [UserResponse(**entity.to_dict()) for entity in results]

    def create(self, entity: UserCreateRequest) -> UserResponse:
        """创建新用户。

        Args:
            entity: 用户创建请求数据

        Returns:
            UserResponse: 创建成功的用户信息

        Raises:
            ValueError: 用户名已存在时抛出
        """
        # 检查用户名是否已存在
        existing_stmt = select(UserEntity).where(UserEntity.username == entity.username)
        existing = self.session.execute(existing_stmt).scalar_one_or_none()

        if existing is not None:
            raise ValueError(f"Username '{entity.username}' already exists")

        # 创建新用户实体
        user_entity = UserEntity(
            username=entity.username,
            email=entity.email,
            name=entity.name,
            age=entity.age,
        )

        self.session.add(user_entity)
        self.session.flush()  # 获取生成的 ID

        return UserResponse(**user_entity.to_dict())

    def update(self, id: int, entity: UserUpdateRequest) -> Optional[UserResponse]:
        """更新用户信息。

        仅更新请求中提供的非空字段。

        Args:
            id: 用户唯一标识
            entity: 用户更新请求数据

        Returns:
            Optional[UserResponse]: 更新后的用户信息，不存在时返回 None
        """
        # 检查用户是否存在
        user_entity = self.session.get(UserEntity, id)
        if user_entity is None:
            return None

        # 构建更新数据
        update_data: dict = entity.model_dump(exclude_unset=True)

        # 更新字段
        for key, value in update_data.items():
            setattr(user_entity, key, value)

        self.session.flush()

        return UserResponse(**user_entity.to_dict())

    def delete(self, id: int) -> bool:
        """删除用户。

        Args:
            id: 用户唯一标识

        Returns:
            bool: 是否删除成功
        """
        user_entity = self.session.get(UserEntity, id)
        if user_entity is None:
            return False

        self.session.delete(user_entity)
        self.session.flush()

        return True

    def count(self) -> int:
        """统计用户总数。

        Returns:
            int: 用户总数
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(UserEntity)
        result = self.session.execute(stmt).scalar()

        return result or 0
