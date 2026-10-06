#!/usr/bin/env python3
"""
用户业务逻辑实现
提供用户 CRUD、登录凭据校验、登录信息记录。

Classes:
    UserService: 用户业务逻辑实现
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from src.constants.constants import SUPERADMIN_USERNAME
from src.constants.enums import NotificationEvent, NotificationSource, UserStatus
from src.constants.permissions import PermissionAction
from src.core.exceptions import AuthorizationException, ConflictException, NotFoundException
from src.core.logger import logger
from src.models.entities.user_entity import UserEntity
from src.notification.decorators import notify
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
from src.schemas.admin.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.admin.base_service import BaseService, audit_crud
from src.utils.security import hash_password, verify_password

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher


class UserService(BaseService[UserResponse, int, UserRepository]):
    """用户业务逻辑实现。
    继承 BaseService 提供的通用能力：
        - get_by_id / get_all / _commit / _audit / _log_action
    本类负责：
        - 用户特有的业务校验（邮箱/用户名唯一性）
        - Entity → UserResponse 转换
        - 登录凭据校验
    """

    entity_type = "user"

    def __init__(
        self,
        user_repository: UserRepository,
        dispatcher: NotificationDispatcher | None = None,
        role_repository: RoleRepository | None = None,
    ) -> None:
        """初始化用户服务。"""
        self._repository: UserRepository = user_repository
        self._dispatcher = dispatcher
        self._role_repository = role_repository

    def search(
        self,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索用户（分页）。"""
        skip = (page - 1) * page_size
        entities, total = self._repository.search(keyword=keyword, status=status, skip=skip, limit=page_size)
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @audit_crud(PermissionAction.CREATE.mark)
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
            name=request.name,
            phone=request.phone,
            gender=request.gender,
            birthday=datetime.strptime(request.birthday, "%Y-%m-%d"),
            avatar_url=request.avatar_url,
            status=request.status.value if isinstance(request.status, UserStatus) else request.status,
        )
        created = self._repository.create(entity)
        self._commit()
        # 绑定多角色（经仓库）
        role_ids = list(dict.fromkeys([rid for rid in (request.role_ids or []) if rid]))
        if role_ids:
            self._repository.replace_user_roles(created.id, role_ids)
            self._commit()
        result = self._to_response(created)
        logger.info(f"User created: id={result.id} username={result.username}")
        return result

    def import_users(self, rows: list[dict[str, Any]], operator: dict[str, Any] | None = None) -> dict[str, Any]:
        """批量导入用户（业务编排层）。

        CSV 文件读取/解码与表格解析由 API 层完成（入参接收），本方法负责：
            1. 默认角色兜底：CSV 行未指定 role_id 时绑定"普通用户(user)"角色
            2. 行级校验：缺 username/email 的行跳过
            3. 逐行组装 payload 并调用 :meth:`create`

        Returns:
            dict[str, Any]: 导入统计 {"imported": int}
        """
        default_role_id: int | None = None
        if self._role_repository is not None:
            default_role = self._role_repository.get_by_code("user")
            default_role_id = default_role.id if default_role else None
        imported = 0
        for row in rows:
            if not row.get("username") or not row.get("email"):
                continue
            csv_role_id = int(row["role_id"]) if row.get("role_id") else None
            role_ids = [csv_role_id] if csv_role_id else ([default_role_id] if default_role_id else [])
            if not role_ids:
                # 系统无可用默认角色时跳过该行，避免必填校验失败
                continue
            payload = {
                "username": row["username"],
                "email": row["email"],
                "password": row.get("password") or "ChangeMe@123",
                "name": row.get("name") or row["username"],
                "phone": row.get("phone") or "",
                "gender": row.get("gender") or "male",
                "birthday": row.get("birthday") or "1970-01-01",
                "avatar_url": row.get("avatar_url"),
                "role_ids": role_ids,
                "status": row.get("status") or "enabled",
            }
            self.create(payload, operator=operator)
            imported += 1
        return {"imported": imported}

    @audit_crud(PermissionAction.EDIT.mark)
    def update(self, id: int, data: dict[str, Any], operator: dict[str, Any] | None = None) -> UserResponse:
        """更新用户信息（密码提供时重新哈希）。"""
        request = UserUpdateRequest(**data)
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")
        # 超级管理员保护：非 superadmin 不能修改 superadmin
        if (
            existing.username == SUPERADMIN_USERNAME
            and operator
            and operator.get("operator_name") != SUPERADMIN_USERNAME
        ):
            raise AuthorizationException(message="不能修改超级管理员账号")
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
            status=existing.status,
        )
        # 空字符串转 None（datetime/int 字段不接受空串）
        for k in ("birthday", "phone", "email", "name"):
            if patch_dict.get(k) == "":
                patch_dict[k] = None
        if patch_dict.get("birthday") and isinstance(patch_dict["birthday"], str):
            from datetime import datetime

            patch_dict["birthday"] = datetime.strptime(patch_dict["birthday"], "%Y-%m-%d")
        for key, value in patch_dict.items():
            if hasattr(patch, key):
                setattr(patch, key, value)
        if "name" in patch_dict:
            patch.name = patch_dict["name"]
        # 更新角色关联（经仓库）
        if "role_ids" in patch_dict:
            role_ids = patch_dict.pop("role_ids")
            self._repository.replace_user_roles(id, role_ids)
        updated = self._repository.update(id, patch)
        if updated is None:
            raise NotFoundException(message=f"用户 {id} 不存在")
        self._commit()
        result = self._to_response(updated)
        logger.info(f"User updated: id={result.id} username={result.username}")
        # 角色变更通知由 @notify 装饰器处理
        # ── 通知：密码变更 ──
        if "password_hash" in patch_dict:
            self._dispatch_notification(
                updated.id,
                NotificationEvent.USER_PASSWORD_CHANGED,
                {"username": updated.username, "changed_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M")},
            )
        else:
            # ── 通知：资料变更 ──
            changed_keys = [k for k in patch_dict if k != "password_hash"]
            if changed_keys:
                self._dispatch_notification(
                    updated.id,
                    NotificationEvent.USER_PROFILE_UPDATED,
                    {"username": updated.username, "updated_fields": "、".join(changed_keys)},
                )
        # ── 通知：状态变更 ──
        if "status" in patch_dict and patch_dict["status"] != existing.status:
            self._dispatch_notification(
                updated.id,
                NotificationEvent.USER_STATUS_CHANGED,
                {
                    "username": updated.username,
                    "new_status": patch_dict["status"],
                    "reason": "管理员操作",
                },
            )
        return result

    @notify(NotificationEvent.USER_DELETED, target="self")
    @audit_crud(PermissionAction.DELETE.mark)
    def delete(self, id: int, operator: dict[str, Any] | None = None) -> bool:
        """软删除用户。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")
        # 超级管理员保护
        if (
            existing.username == SUPERADMIN_USERNAME
            and operator
            and operator.get("operator_name") != SUPERADMIN_USERNAME
        ):
            raise AuthorizationException(message="不能删除超级管理员账号")
        deleted = self._repository.delete(id)
        if deleted:
            self._commit()
            logger.info(f"User deleted: id={id} username={existing.username}")
        return deleted

    def reset_password(self, id: int, new_password: str, operator: dict[str, Any] | None = None) -> bool:
        """管理员重置用户密码。"""
        existing = self._repository.get_by_id(id)
        if existing is None:
            raise NotFoundException(message=f"用户 {id} 不存在")
        # 超级管理员保护
        if (
            existing.username == SUPERADMIN_USERNAME
            and operator
            and operator.get("operator_name") != SUPERADMIN_USERNAME
        ):
            raise AuthorizationException(message="不能重置超级管理员密码")
        existing.password_hash = hash_password(new_password)
        self._commit()
        self._audit(
            entity_id=id,
            action=PermissionAction.EDIT.mark,
            operator=operator,
            before_data={"username": existing.username},
            after_data={"username": existing.username, "action": "password_reset"},
            remarks=f"管理员重置用户{existing.username}的密码",
        )
        logger.info(f"Password reset by admin: user_id={id}")
        # ── 通知：密码变更 ──
        self._dispatch_notification(
            id,
            NotificationEvent.USER_PASSWORD_CHANGED,
            {"username": existing.username, "changed_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M")},
        )
        return True

    def verify_credentials(self, account: str, password: str) -> UserEntity | None:
        """校验登录凭据（供 AuthService 调用）。
        支持用户名或邮箱匹配；DISABLED 用户拒绝登录。
        """
        user: UserEntity | None
        user = self._repository.get_by_email(account) if "@" in account else self._repository.get_by_username(account)
        if user is None:
            return None
        if user.status == UserStatus.DISABLED.value:
            return None
        if not verify_password(password, user.password_hash or ""):
            return None
        return user

    def _to_response(self, entity: UserEntity) -> UserResponse:
        """实体转响应 DTO，关联查询角色列表（经仓库）。"""
        # 查询用户角色列表
        roles = []
        user_roles = self._repository.get_roles_by_user_id(entity.id)
        for role in user_roles:
            roles.append({"id": role.id, "role_name": role.role_name, "role_code": role.role_code})
        return UserResponse(
            id=entity.id,
            username=entity.username,
            email=entity.email,
            name=entity.name,
            gender=entity.gender,
            birthday=entity.birthday.strftime("%Y-%m-%d"),
            phone=entity.phone,
            avatar_url=entity.avatar_url,
            roles=roles,
            status=entity.status or UserStatus.ENABLED.value,
            last_login_at=entity.last_login_at,
            last_login_ip=entity.last_login_ip,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _find_by_email(self, email: str) -> UserEntity | None:
        finder = getattr(self._repository, "get_by_email", None)
        if finder is not None:
            return cast(UserEntity | None, finder(email))
        return next((item for item in self._repository.get_all() if item.email == email), None)

    def _find_by_username(self, username: str) -> UserEntity | None:
        finder = getattr(self._repository, "get_by_username", None)
        if finder is not None:
            return cast(UserEntity | None, finder(username))
        return next((item for item in self._repository.get_all() if item.username == username), None)

    def _dispatch_notification(
        self,
        user_id: int,
        event_type: NotificationEvent,
        variables: dict[str, Any],
    ) -> None:
        """发送通知（失败不阻断业务主流程）。"""
        if self._dispatcher is None:
            return
        try:
            self._dispatcher.dispatch_for_user(
                user_id=user_id,
                event_type=event_type,
                variables=variables,
                source=NotificationSource.MANUAL.value,
            )
        except Exception as e:
            logger.warning(f"通知发送失败（不影响业务）: event={event_type.value} user={user_id} error={e}")
