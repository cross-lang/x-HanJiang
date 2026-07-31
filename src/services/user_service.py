#!/usr/bin/env python3
"""
用户业务逻辑实现

本模块提供用户 Service 的具体实现，作为项目模板的示例代码。
通过构造函数注入 UserRepository，演示依赖注入的使用方式。

Classes:
    UserService: 用户业务逻辑实现
"""

from typing import Any

from src.core.exceptions import NotFoundException
from src.core.logger import logger
from src.models.entities.user_entity import UserEntity
from src.repositories.user_repository import UserRepository
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.base_service import BaseService


def _entity_to_response(entity: UserEntity) -> UserResponse:
    """将 ORM 实体转为 API 响应 DTO。

    Args:
        entity: UserEntity 实例

    Returns:
        UserResponse: API 响应模型
    """
    return UserResponse(**entity.to_dict())


class UserService(BaseService[UserResponse, int]):
    """用户业务逻辑实现。

    通过构造函数注入 UserRepository 实例，实现用户相关的业务逻辑。
    业务逻辑层负责：
        1. DTO 与 Entity 之间的转换
        2. 业务规则校验（用户名唯一性、邮箱格式等）
        3. 业务异常包装（资源不存在、冲突等）

    Attributes:
        _repository: 用户数据访问实例
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self._repository: UserRepository = user_repository

    def get_by_id(self, id: int) -> UserResponse | None:
        """根据用户 ID 查询用户。

        Args:
            id: 用户唯一标识

        Returns:
            Optional[UserResponse]: 用户响应 DTO，不存在时返回 None
        """
        entity = self._repository.get_by_id(id)
        return _entity_to_response(entity) if entity else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有用户（分页）。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页记录数

        Returns:
            dict[str, Any]: 包含 items、total、page、page_size 的分页结果字典
        """
        skip: int = (page - 1) * page_size
        entities = self._repository.get_all(skip=skip, limit=page_size)
        items = [_entity_to_response(e) for e in entities]
        total = self._repository.count()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create(self, data: dict[str, Any]) -> UserResponse:
        """创建新用户。

        将字典数据转换为 UserCreateRequest 模型，构造 Entity 后调用 Repository。

        Args:
            data: 用户创建数据字典

        Returns:
            UserResponse: 创建成功的用户响应

        Raises:
            ConflictException: 用户名或邮箱唯一约束冲突时抛出
        """
        request = UserCreateRequest(**data)
        entity = UserEntity(
            username=request.username,
            email=request.email,
            name=request.name,
            age=request.age,
        )
        created = self._repository.create(entity)
        result = _entity_to_response(created)
        logger.info(f"User created: id={result.id} username={result.username}")
        return result

    def update(self, id: int, data: dict[str, Any]) -> UserResponse:
        """更新用户信息。

        Args:
            id: 用户唯一标识
            data: 更新数据字典

        Returns:
            UserResponse: 更新后的用户响应

        Raises:
            NotFoundException: 用户不存在时抛出
            ConflictException: 用户名/邮箱唯一约束冲突时抛出
        """
        request = UserUpdateRequest(**data)
        # 构造临时 Entity 仅用于承载待更新字段
        patch = UserEntity(
            username="",  # 不会写入（to_dict 后不会赋 username）
            email=request.email or "",
            name=request.name or "",
            age=request.age,
        )
        # 用 model_dump 仅保留 request 中显式提供的字段
        patch_dict = request.model_dump(exclude_unset=True)
        for key, value in patch_dict.items():
            setattr(patch, key, value)

        updated = self._repository.update(id, patch)
        if updated is None:
            raise NotFoundException(message=f"User with id {id} not found")

        result = _entity_to_response(updated)
        logger.info(f"User updated: id={result.id} username={result.username}")
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
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"User with id {id} not found")

        if self._repository.delete(id):
            logger.info(f"User deleted: id={id} username={existing.username}")
            return True
        return False
