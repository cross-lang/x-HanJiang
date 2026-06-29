#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户业务逻辑实现

本模块提供用户 Service 的具体实现，作为项目模板的示例代码。
通过构造函数注入 UserRepository，演示依赖注入的使用方式。

Classes:
    UserService: 用户业务逻辑实现
"""

from typing import Any, Optional

from src.models.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.repository.user_repository import UserRepository
from src.service.base_service import BaseService


class UserService(BaseService[UserResponse, int]):
    """用户业务逻辑实现。

    通过构造函数注入 UserRepository 实例，实现用户相关的业务逻辑。
    业务逻辑层负责数据校验、业务规则检查和流程编排。

    Attributes:
        _repository: 用户数据访问实例
    """

    def __init__(self, user_repository: UserRepository) -> None:
        """初始化用户服务。

        Args:
            user_repository: 用户数据访问实例（通过 DI 容器自动注入）
        """
        self._repository: UserRepository = user_repository

    def get_by_id(self, id: int) -> Optional[UserResponse]:
        """根据用户 ID 查询用户。

        Args:
            id: 用户唯一标识

        Returns:
            Optional[UserResponse]: 用户信息，不存在时返回 None
        """
        return self._repository.get_by_id(id)

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有用户（分页）。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页记录数

        Returns:
            dict[str, Any]: 包含 items、total、page、page_size 的分页结果字典
        """
        skip: int = (page - 1) * page_size
        items: list[UserResponse] = self._repository.get_all(skip=skip, limit=page_size)
        total: int = self._repository.count()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create(self, data: dict[str, Any]) -> UserResponse:
        """创建新用户。

        将字典数据转换为 UserCreateRequest 模型，调用 Repository 执行创建。

        Args:
            data: 用户创建数据字典

        Returns:
            UserResponse: 创建成功的用户信息

        Raises:
            BusinessException: 用户名已存在或其他业务规则违反时抛出
        """
        from src.core.exceptions import BusinessException
        from src.core.logger import logger

        try:
            request: UserCreateRequest = UserCreateRequest(**data)
            result: UserResponse = self._repository.create(request)
            logger.info(f"User created: {result.username}")
            return result
        except ValueError as e:
            raise BusinessException(message=str(e), code=400)

    def update(self, id: int, data: dict[str, Any]) -> Optional[UserResponse]:
        """更新用户信息。

        Args:
            id: 用户唯一标识
            data: 更新数据字典

        Returns:
            Optional[UserResponse]: 更新后的用户信息，不存在时返回 None

        Raises:
            BusinessException: 用户不存在时抛出
        """
        from src.core.exceptions import NotFoundException
        from src.core.logger import logger

        request: UserUpdateRequest = UserUpdateRequest(**data)
        result: Optional[UserResponse] = self._repository.update(id, request)

        if result is None:
            raise NotFoundException(message=f"User with id {id} not found")

        logger.info(f"User updated: {result.username}")
        return result

    def delete(self, id: int) -> bool:
        """删除用户。

        Args:
            id: 用户唯一标识

        Returns:
            bool: 是否删除成功

        Raises:
            NotFoundException: 用户不存在时抛出
        """
        from src.core.exceptions import NotFoundException
        from src.core.logger import logger

        existing: Optional[UserResponse] = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"User with id {id} not found")

        result: bool = self._repository.delete(id)
        if result:
            logger.info(f"User deleted: {existing.username}")
        return result
