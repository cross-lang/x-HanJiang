#!/usr/bin/env python3
"""
用户业务逻辑实现

Classes:
    UserService: 用户业务逻辑实现
"""

from typing import Any

from src.constants.enums import CommonStatus, UserStatus
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from src.core.logger import logger
from src.core.security import hash_password, verify_password
from src.models.entities.user_entity import UserEntity
from src.repositories.role_repository import RoleRepository
from src.repositories.tenant_repository import TenantRepository
from src.repositories.user_repository import UserRepository
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.audit_service import AuditService
from src.services.base_service import BaseService


class UserService(BaseService[UserResponse, int]):
    """用户业务逻辑实现。

    Attributes:
        _repository: 用户数据访问实例
        _tenant_repository: 租户数据访问实例（校验租户存在与配额）
        _role_repository: 角色数据访问实例（导出联查）
        _audit_service: 审计日志服务
    """

    def __init__(
        self,
        user_repository: UserRepository,
        tenant_repository: TenantRepository | None = None,
        role_repository: RoleRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        """初始化用户服务。"""
        self._repository: UserRepository = user_repository
        self._tenant_repository = tenant_repository or TenantRepository(
            session=user_repository.session
        )
        self._role_repository = role_repository or RoleRepository(
            session=user_repository.session
        )
        self._audit_service = audit_service

    def get_by_id(self, id: int) -> UserResponse | None:
        """根据用户 ID 查询用户。"""
        entity = self._repository.get_by_id(id)
        return self._to_response(entity) if entity else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有用户（分页）。"""
        skip = (page - 1) * page_size
        entities = self._repository.get_all(skip=skip, limit=page_size)
        return {
            "items": [self._to_response(e) for e in entities],
            "total": self._repository.count_all(),
            "page": page,
            "page_size": page_size,
        }

    def search(
        self,
        tenant_id: int | None = None,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索用户（分页）。

        Args:
            tenant_id: 租户过滤
            keyword: 关键字（用户名/邮箱）
            status: 状态过滤
            page: 页码
            page_size: 每页记录数

        Returns:
            dict: 分页结果
        """
        skip = (page - 1) * page_size
        entities, total = self._repository.search(
            tenant_id=tenant_id, keyword=keyword, status=status,
            skip=skip, limit=page_size,
        )
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create(self, data: dict[str, Any], operator: dict[str, Any] | None = None) -> UserResponse:
        """创建新用户。

        业务校验：
            1. 租户必须存在且启用
            2. 租户内用户数不能超过租户 user_quota
            3. 同租户内用户名唯一
            4. 邮箱全局唯一

        Args:
            data: 用户创建数据
            operator: 操作者上下文（用于审计）

        Returns:
            UserResponse: 创建成功的用户响应

        Raises:
            NotFoundException: 租户不存在时抛出
            ValidationException: 租户已停用/配额已满时抛出
            ConflictException: 用户名或邮箱冲突时抛出
        """
        request = UserCreateRequest(**data)

        tenant = self._tenant_repository.get_by_id(request.tenant_id)
        if tenant is None:
            raise NotFoundException(message=f"租户 {request.tenant_id} 不存在")
        if tenant.status == CommonStatus.DISABLED:
            raise ValidationException(message=f"租户 {tenant.tenant_name} 已停用，无法添加用户")

        # 配额校验
        current_users = self._repository.count_by_tenant(request.tenant_id)
        if current_users >= tenant.user_quota:
            raise ValidationException(
                message=f"租户用户数已达配额上限（{current_users}/{tenant.user_quota}）"
            )

        # 用户名租户内唯一校验
        existing_by_name = self._repository.get_by_username(request.username)
        if (
            existing_by_name is not None
            and existing_by_name.tenant_id == request.tenant_id
        ):
            raise ConflictException(
                message=f"用户名 {request.username} 在租户内已存在"
            )

        # 邮箱全局唯一校验
        if self._repository.get_by_email(request.email) is not None:
            raise ConflictException(message=f"邮箱 {request.email} 已被注册")

        entity = UserEntity(
            tenant_id=request.tenant_id,
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            phone=request.phone,
            avatar_url=request.avatar_url,
            role_id=request.role_id,
            status=request.status,
        )
        created = self._repository.create(entity)
        self._commit(self._repository)
        result = self._to_response(created)
        logger.info(f"User created: id={result.id} username={result.username}")

        self._record_audit(
            operator=operator,
            tenant_id=result.tenant_id,
            action="create",
            resource_type="user",
            resource_id=result.id,
            detail=f"创建用户 {result.username}({result.email})",
        )
        return result

    def update(
        self, id: int, data: dict[str, Any], operator: dict[str, Any] | None = None
    ) -> UserResponse:
        """更新用户信息。

        Args:
            id: 用户ID
            data: 更新数据（仅包含显式提供的字段）
            operator: 操作者上下文

        Returns:
            UserResponse: 更新后的用户响应

        Raises:
            NotFoundException: 用户不存在时抛出
            ConflictException: 邮箱冲突时抛出
        """
        request = UserUpdateRequest(**data)
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")

        patch_dict = request.model_dump(exclude_unset=True)

        # 邮箱冲突校验
        if "email" in patch_dict and patch_dict["email"] != existing.email:
            other = self._repository.get_by_email(patch_dict["email"])
            if other is not None and other.id != id:
                raise ConflictException(message=f"邮箱 {patch_dict['email']} 已被其他用户占用")

        # 密码重新哈希
        if "password" in patch_dict and patch_dict["password"]:
            patch_dict["password_hash"] = hash_password(patch_dict.pop("password"))
        else:
            patch_dict.pop("password", None)

        patch = UserEntity(
            id=id,
            tenant_id=existing.tenant_id,
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

        updated = self._repository.update(id, patch)
        if updated is None:
            raise NotFoundException(message=f"用户 {id} 不存在")
        self._commit(self._repository)
        result = self._to_response(updated)
        logger.info(f"User updated: id={result.id} username={result.username}")

        self._record_audit(
            operator=operator,
            tenant_id=result.tenant_id,
            action="update",
            resource_type="user",
            resource_id=result.id,
            detail=f"更新用户 {result.username}: {list(patch_dict.keys())}",
        )
        return result

    def delete(self, id: int, operator: dict[str, Any] | None = None) -> bool:
        """软删除用户。

        Args:
            id: 用户ID
            operator: 操作者上下文

        Returns:
            bool: 是否删除成功

        Raises:
            NotFoundException: 用户不存在时抛出
        """
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")

        deleted = self._repository.delete(id)
        if deleted:
            self._commit(self._repository)
            logger.info(f"User deleted: id={id} username={existing.username}")
            self._record_audit(
                operator=operator,
                tenant_id=existing.tenant_id,
                action="delete",
                resource_type="user",
                resource_id=id,
                detail=f"删除用户 {existing.username}({existing.email})",
            )
        return deleted

    def verify_credentials(self, account: str, password: str) -> UserEntity | None:
        """校验登录凭据（供 AuthService 调用）。

        支持用户名或邮箱匹配；用户名重名时返回第一条并依赖密码校验。

        Args:
            account: 用户名或邮箱
            password: 明文密码

        Returns:
            Optional[UserEntity]: 校验通过的用户实体，失败返回 None
        """
        user: UserEntity | None
        if "@" in account:
            user = self._repository.get_by_email(account)
        else:
            user = self._repository.get_by_username(account)

        if user is None:
            return None
        if user.status == UserStatus.LOCKED:
            return None
        if not verify_password(password, user.password_hash or ""):
            return None
        return user

    def record_login_success(self, user_id: int, ip_address: str | None) -> None:
        """更新用户最后登录信息。

        Args:
            user_id: 用户ID
            ip_address: 登录IP
        """
        from datetime import UTC, datetime

        user = self._repository.get_by_id(user_id)
        if user is None:
            return
        user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
        user.last_login_ip = ip_address
        self._repository.session.flush()

    def _to_response(self, entity: UserEntity) -> UserResponse:
        """实体转响应 DTO。"""
        return UserResponse(
            id=entity.id,
            tenant_id=entity.tenant_id,
            username=entity.username,
            email=entity.email,
            phone=entity.phone,
            avatar_url=entity.avatar_url,
            role_id=entity.role_id,
            status=entity.status.value if entity.status else "active",
            last_login_at=entity.last_login_at,
            last_login_ip=entity.last_login_ip,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def export_users(
        self,
        tenant_id: int | None = None,
        keyword: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """导出用户列表（按筛选条件导出全部匹配项，联查名称字段）。

        返回扁平字典列表，字段对应导出表格列：
        用户名 / 邮箱 / 角色 / 所属租户 / 所属空间 / 状态 / 最后登录。

        Args:
            tenant_id: 租户过滤
            keyword: 关键字（匹配用户名或邮箱）
            status: 状态过滤

        Returns:
            list[dict]: 用户导出行列表
        """
        users, _ = self._repository.search(
            tenant_id=tenant_id,
            keyword=keyword,
            status=status,
            skip=0,
            limit=100000,
        )
        if not users:
            return []

        # 批量收集关联 ID，避免 N+1
        role_ids = {u.role_id for u in users if u.role_id is not None}
        tenant_ids = {u.tenant_id for u in users if u.tenant_id is not None}

        role_map = {
            r.id: r.role_name for r in (self._role_repository.get_by_id(rid) for rid in role_ids) if r
        }
        tenant_map = {
            t.id: t.tenant_name for t in (self._tenant_repository.get_by_id(tid) for tid in tenant_ids) if t
        }

        rows: list[dict[str, Any]] = []
        for u in users:
            last_login = (
                u.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if u.last_login_at else ""
            )
            rows.append(
                {
                    "username": u.username,
                    "email": u.email or "",
                    "role_name": role_map.get(u.role_id, "") if u.role_id is not None else "",
                    "tenant_name": tenant_map.get(u.tenant_id, "") if u.tenant_id is not None else "",
                    "status": u.status.value if u.status else "active",
                    "last_login_at": last_login,
                }
            )
        return rows

    def _commit(self, repository: UserRepository) -> None:
        """提交当前会话事务（session 为 None 时跳过，便于测试替身）。"""
        if repository.session is None:
            return
        try:
            repository.session.commit()
        except Exception as e:  # noqa: BLE001
            repository.session.rollback()
            raise e

    def _record_audit(
        self,
        operator: dict[str, Any] | None,
        tenant_id: int | None,
        action: str,
        resource_type: str,
        resource_id: int | None,
        detail: str,
    ) -> None:
        """记录审计日志（失败不影响主流程）。"""
        if not self._audit_service:
            return
        ctx = operator or {}
        try:
            self._audit_service.log(
                tenant_id=tenant_id,
                user_id=ctx.get("user_id"),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                ip_address=ctx.get("ip_address"),
                user_agent=ctx.get("user_agent"),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to write audit log: {e}")
