#!/usr/bin/env python3
"""
用户业务逻辑实现

提供用户 CRUD、登录凭据校验、登录信息记录。
不依赖 role/audit 等已移除的模块。

Classes:
    UserService: 用户业务逻辑实现
"""

from datetime import UTC, datetime
from typing import Any

from src.constants.enums import UserStatus
from src.core.exceptions import ConflictException, NotFoundException, ValidationException
from src.core.logger import logger
from src.core.security import hash_password, verify_password
from src.models.entities.user_entity import UserEntity
from src.repositories.user_repository import UserRepository
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.base_service import BaseService


class UserService(BaseService[UserResponse, int]):
    """用户业务逻辑实现。

    Attributes:
        _repository: 用户数据访问实例
    """

    def __init__(self, user_repository: UserRepository) -> None:
        """初始化用户服务。"""
        self._repository: UserRepository = user_repository

    def get_by_id(self, id: int) -> UserResponse | None:
        """根据用户 ID 查询用户。"""
        entity = self._repository.get_by_id(id)
        return self._to_response(entity) if entity else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有用户（分页）。"""
        skip = (page - 1) * page_size
        entities = self._repository.get_all(skip=skip, limit=page_size)
        total = getattr(self._repository, "count_all", None)
        if callable(total):
            total_count = total()
        else:
            total_count = self._repository.count()
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total_count,
            "page": page,
            "page_size": page_size,
        }

    def search(
        self,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索用户（分页）。"""
        skip = (page - 1) * page_size
        entities, total = self._repository.search(
            keyword=keyword, status=status, skip=skip, limit=page_size
        )
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create(self, data: dict[str, Any], operator: dict[str, Any] | None = None) -> UserResponse:
        """创建新用户.

        业务校验：
            1. 邮箱全局唯一
            2. 用户名全局唯一
        """
        request = UserCreateRequest(**data)

        if self._find_by_email(request.email) is not None:
            raise ConflictException(message=f"邮箱 {request.email} 已被注册")
        if self._find_by_username(request.username) is not None:
            raise ConflictException(message=f"用户名 {request.username} 已存在")

        entity = UserEntity(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            phone=request.phone,
            avatar_url=request.avatar_url,
            role_id=request.role_id,
            status=request.status.value if isinstance(request.status, UserStatus) else request.status,
        )
        if getattr(request, "name", None) is not None:
            entity.name = request.name
        if getattr(request, "age", None) is not None:
            entity.age = request.age
        created = self._repository.create(entity)
        self._commit()

        self._audit(
            entity_id=created.id,
            action="create",
            operator=operator,
            before_data=None,
            after_data={"username": created.username, "email": created.email, "role_id": created.role_id},
            remarks="user created",
        )

        result = self._to_response(created)
        logger.info(f"User created: id={result.id} username={result.username}")
        return result

    def update(
        self, id: int, data: dict[str, Any], operator: dict[str, Any] | None = None
    ) -> UserResponse:
        """更新用户信息（密码提供时重新哈希）。"""
        request = UserUpdateRequest(**data)
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")

        patch_dict = request.model_dump(exclude_unset=True)

        if "email" in patch_dict and patch_dict["email"] != existing.email:
            other = self._find_by_email(patch_dict["email"])
            if other is not None and other.id != id:
                raise ConflictException(message=f"邮箱 {patch_dict['email']} 已被其他用户占用")

        if "password" in patch_dict and patch_dict["password"]:
            patch_dict["password_hash"] = hash_password(patch_dict.pop("password"))
        else:
            patch_dict.pop("password", None)

        patch = UserEntity(
            id=id,
            username=existing.username,
            email=existing.email,
            password_hash=existing.password_hash,
            phone=existing.phone,
            avatar_url=existing.avatar_url,
            role_id=existing.role_id,
            status=existing.status,
        )
        for key, value in patch_dict.items():
            if hasattr(patch, key):
                setattr(patch, key, value)
        if "name" in patch_dict:
            setattr(patch, "name", patch_dict["name"])
        if "age" in patch_dict:
            setattr(patch, "age", patch_dict["age"])

        updated = self._repository.update(id, patch)
        if updated is None:
            raise NotFoundException(message=f"用户 {id} 不存在")
        self._commit()

        self._audit(
            entity_id=updated.id,
            action="update",
            operator=operator,
            before_data={"username": existing.username, "email": existing.email, "role_id": existing.role_id},
            after_data={"username": updated.username, "email": updated.email, "role_id": updated.role_id},
            remarks="user updated",
        )

        result = self._to_response(updated)
        logger.info(f"User updated: id={result.id} username={result.username}")
        return result

    def delete(self, id: int, operator: dict[str, Any] | None = None) -> bool:
        """软删除用户。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")

        deleted = self._repository.delete(id)
        if deleted:
            self._commit()
            self._audit(
                entity_id=id,
                action="delete",
                operator=operator,
                before_data={"username": existing.username, "email": existing.email, "role_id": existing.role_id},
                after_data=None,
                remarks="user deleted",
            )
            logger.info(f"User deleted: id={id} username={existing.username}")
        return deleted

    def verify_credentials(self, account: str, password: str) -> UserEntity | None:
        """校验登录凭据（供 AuthService 调用）。

        支持用户名或邮箱匹配；LOCKED 用户拒绝登录。
        """
        user: UserEntity | None
        if "@" in account:
            user = self._repository.get_by_email(account)
        else:
            user = self._repository.get_by_username(account)

        if user is None:
            return None
        if user.status == UserStatus.LOCKED.value:
            return None
        if not verify_password(password, user.password_hash or ""):
            return None
        return user

    def _to_response(self, entity: UserEntity) -> UserResponse:
        """实体转响应 DTO。"""
        return UserResponse(
            id=entity.id,
            username=entity.username,
            email=entity.email,
            name=getattr(entity, "name", None),
            age=getattr(entity, "age", None),
            phone=entity.phone,
            avatar_url=entity.avatar_url,
            role_id=entity.role_id,
            status=entity.status or UserStatus.ACTIVE.value,
            last_login_at=entity.last_login_at,
            last_login_ip=entity.last_login_ip,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _find_by_email(self, email: str) -> UserEntity | None:
        finder = getattr(self._repository, "get_by_email", None)
        if finder is not None:
            return finder(email)
        return next((item for item in self._repository.get_all() if item.email == email), None)

    def _find_by_username(self, username: str) -> UserEntity | None:
        finder = getattr(self._repository, "get_by_username", None)
        if finder is not None:
            return finder(username)
        return next((item for item in self._repository.get_all() if item.username == username), None)

    def _audit(
        self,
        entity_id: int,
        action: str,
        operator: dict[str, Any] | None,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
        remarks: str,
    ) -> None:
        if not hasattr(self._repository, "session"):
            return
        from src.services.audit_service import AuditService

        AuditService().log_event(
            entity_type="user",
            entity_id=entity_id,
            action=action,
            operator_id=operator.get("operator_id") if operator else None,
            operator_name=operator.get("operator_name") if operator else None,
            before_data=before_data,
            after_data=after_data,
            ip_address=operator.get("ip_address") if operator else None,
            remarks=remarks,
        )

    def _commit(self) -> None:
        """提交当前会话事务。测试用的内存仓库没有 SQLAlchemy session，需安全忽略。"""
        session = getattr(self._repository, "session", None)
        if session is None:
            return

        try:
            session.commit()
        except Exception as e:  # noqa: BLE001
            if hasattr(session, "rollback"):
                session.rollback()
            raise e
