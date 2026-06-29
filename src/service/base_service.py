#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务逻辑层抽象基类

本模块定义了业务逻辑层的标准接口契约，所有 Service 实现类必须继承此基类。
提供通用的业务操作接口定义，确保业务逻辑层的统一规范。

类型参数：
    T: 实体类型
    ID: 主键类型

Classes:
    BaseService: 业务逻辑层抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class BaseService(ABC, Generic[T, ID]):
    """业务逻辑层抽象基类。

    定义标准业务操作接口，所有业务逻辑实现类必须继承此基类并实现全部抽象方法。
    业务逻辑层负责处理业务规则、数据校验和业务流程编排。

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
    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有实体（分页）。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页记录数

        Returns:
            dict[str, Any]: 包含 items（数据列表）、total（总数）、page、page_size 的字典
        """

    @abstractmethod
    def create(self, data: dict[str, Any]) -> T:
        """创建新实体。

        Args:
            data: 实体创建数据

        Returns:
            T: 创建成功的实体

        Raises:
            BusinessException: 业务规则校验失败时抛出
        """

    @abstractmethod
    def update(self, id: ID, data: dict[str, Any]) -> Optional[T]:
        """更新实体。

        Args:
            id: 待更新实体的主键
            data: 更新数据

        Returns:
            Optional[T]: 更新成功的实体，不存在时返回 None

        Raises:
            BusinessException: 业务规则校验失败时抛出
        """

    @abstractmethod
    def delete(self, id: ID) -> bool:
        """删除实体。

        Args:
            id: 待删除实体的主键

        Returns:
            bool: 是否删除成功
        """
