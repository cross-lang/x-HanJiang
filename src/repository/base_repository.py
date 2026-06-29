#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据访问层抽象基类

本模块定义了数据访问层的标准接口契约，所有 Repository 实现类必须继承此基类。
提供通用的 CRUD 操作接口定义，确保数据访问层的统一规范。

类型参数：
    T: 实体类型
    ID: 主键类型

Classes:
    BaseRepository: 数据访问层抽象基类
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class BaseRepository(ABC, Generic[T, ID]):
    """数据访问层抽象基类。

    定义标准 CRUD 操作接口，所有数据访问实现类必须继承此基类并实现全部抽象方法。
    通过泛型参数 T 和 ID 支持任意实体类型和主键类型。

    Type Parameters:
        T: 实体类型
        ID: 主键类型
    """

    @abstractmethod
    def get_by_id(self, id: ID) -> Optional[T]:
        """根据主键查询实体。

        Args:
            id: 实体主键

        Returns:
            Optional[T]: 查询到的实体，不存在时返回 None
        """

    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """查询所有实体（分页）。

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            List[T]: 实体列表
        """

    @abstractmethod
    def create(self, entity: T) -> T:
        """创建新实体。

        Args:
            entity: 待创建的实体数据

        Returns:
            T: 创建成功的实体（通常包含生成的主键）

        Raises:
            DatabaseException: 数据库操作失败时抛出
        """

    @abstractmethod
    def update(self, id: ID, entity: T) -> Optional[T]:
        """更新实体。

        Args:
            id: 待更新实体的主键
            entity: 更新后的实体数据

        Returns:
            Optional[T]: 更新成功的实体，不存在时返回 None

        Raises:
            DatabaseException: 数据库操作失败时抛出
        """

    @abstractmethod
    def delete(self, id: ID) -> bool:
        """删除实体。

        Args:
            id: 待删除实体的主键

        Returns:
            bool: 是否删除成功（True 表示成功，False 表示实体不存在）

        Raises:
            DatabaseException: 数据库操作失败时抛出
        """

    @abstractmethod
    def count(self) -> int:
        """统计实体总数。

        Returns:
            int: 实体总数
        """
