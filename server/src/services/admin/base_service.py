#!/usr/bin/env python3
"""
业务逻辑层抽象基类
本模块定义了业务逻辑层的标准接口契约，所有标准 CRUD 业务服务必须继承此基类。
提供通用的业务操作实现，消除子类中的重复代码。
设计原则：
    1. 单一职责：只负责协调 Repository 和 AuditService
    2. 开闭原则：通用逻辑在基类实现，业务差异在子类覆盖
    3. 依赖倒置：依赖 Repository 抽象而非具体实现
继承体系：
    BaseService[T, ID, RepoType]
    ├── UserService(BaseService[UserResponse, int, UserRepository])
    ├── RoleService(BaseService[RoleResponse, int, RoleRepository])
    └── PermissionService(BaseService[PermissionResponse, int, PermissionRepository])
    不继承 BaseService 的服务（有特殊职责）：
    ├── AuthService        # 认证流程，非实体 CRUD
    ├── FileStorageService # 文件存储，非数据库实体
    ├── AlertService       # 告警通知，无 Repository
    └── AuditService       # 审计日志，是其他 Service 的依赖

Usage:
    from src.services.admin.base_service import BaseService
    from src.schemas.admin.user import UserResponse
    class UserService(BaseService[UserResponse, int, UserRepository]):
        entity_type = "user"  # 用于审计日志
        def _to_response(self, entity):
            return UserResponse.model_validate(entity)
        # get_by_id, get_all, create, update, delete 已在基类实现
        # 如需自定义逻辑，覆盖对应方法即可
类型参数：
    T: DTO 响应类型（如 UserResponse）
    ID: 主键类型（如 int）
    RepoType: Repository 类型（如 UserRepository）
"""

import functools
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from src.constants.permissions import PermissionAction
from src.core.logger import logger
from src.repositories.base_repository import BaseRepository

# 审计快照中必须剔除的敏感字段
_SENSITIVE_SNAPSHOT_FIELDS = frozenset({
    "password_hash",
    "hashed_password",
    "app_key_hash",
    "app_key_encrypted",
})
# 从快照中挑选用于 remarks 的展示标签字段（按优先级）
_LABEL_FIELDS = ("username", "role_name", "title", "name")


def _json_safe(value: Any) -> Any:
    """将不可 JSON 序列化的标量值转为可序列化形式。"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _snapshot(entity: Any) -> dict[str, Any] | None:
    """将 ORM 实体或 Pydantic DTO 转为审计快照字典。

    自动剔除密码等敏感字段；datetime/Decimal 转字符串以保证 JSON 可序列化。

    Args:
        entity: ORM 实体（含 ``__table__.columns``）或 Pydantic DTO（含 ``model_dump``）。

    Returns:
        dict | None: 快照字典；实体为 None 或无法识别时返回 None。
    """
    if entity is None:
        return None
    table = getattr(entity, "__table__", None)
    if table is not None:
        return {
            c.name: _json_safe(getattr(entity, c.name, None))
            for c in table.columns
            if c.name not in _SENSITIVE_SNAPSHOT_FIELDS
        } or None
    dump = getattr(entity, "model_dump", None)
    if callable(dump):
        try:
            raw = dump()
        except Exception:
            return None
        return {
            k: _json_safe(v)
            for k, v in raw.items()
            if k not in _SENSITIVE_SNAPSHOT_FIELDS
        } or None
    return None


def _pick_label(snapshot: dict[str, Any] | None) -> str:
    """从快照中挑选用于 remarks 展示的实体名称。"""
    if not snapshot:
        return ""
    for field in _LABEL_FIELDS:
        value = snapshot.get(field)
        if value:
            return str(value)
    return ""


def audit_crud(action: str) -> Callable:
    """CRUD 审计切面装饰器（BaseService 子类专用）。

    自动在方法成功返回后写入审计日志，约定如下：

    - CREATE：被装饰方法返回新建的 ORM 实体或 DTO，entity_id 取返回值 ``.id``，
      before_data=None，after_data=返回值快照；
    - EDIT：第一个位置参数为 entity_id，执行前自动查库取 before_data 快照，
      after_data=返回值快照；
    - DELETE：第一个位置参数为 entity_id，执行前自动查库取 before_data 快照，
      after_data=None；若方法返回 falsy（软删未生效）则不写审计。

    通用约定：
    - operator 由被装饰方法的 ``operator`` 关键字参数传入；
    - 快照自动剔除密码等敏感字段，datetime/Decimal 自动转字符串；
    - 方法抛异常时不写审计（异常向上传播，审计失败本身不阻断业务）。

    Args:
        action: 审计动作 mark，取 :class:`PermissionAction` 的成员。

    Returns:
        方法装饰器。
    """
    action_desc = PermissionAction.get_desc_by_mark(action, action)

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(self: "BaseService", *args: Any, **kwargs: Any) -> Any:
            operator = kwargs.get("operator")
            before_data: dict[str, Any] | None = None
            entity_id: Any = None

            if action != PermissionAction.CREATE.mark:
                entity_id = args[0] if args else None
                before_data = _snapshot(self._repository.get_by_id(entity_id))

            result = fn(self, *args, **kwargs)

            if action == PermissionAction.DELETE.mark:
                if not result:
                    return result
                after_data = None
            elif action == PermissionAction.CREATE.mark:
                # 部分创建方法返回 (实体, 附属值) 元组（如明文密钥），实体取首元素
                entity = result[0] if isinstance(result, tuple) else result
                entity_id = getattr(entity, "id", None)
                after_data = _snapshot(entity)
            else:
                after_data = _snapshot(result)

            label = _pick_label(after_data) or _pick_label(before_data)
            self._audit(
                entity_id=entity_id,
                action=action,
                operator=operator,
                before_data=before_data,
                after_data=after_data,
                remarks=f"{action_desc} {self.entity_type}「{label}」" if label else None,
            )
            return result

        return wrapper

    return decorator

T = TypeVar("T")
ID = TypeVar("ID")
RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(ABC, Generic[T, ID, RepoType]):
    """业务逻辑层抽象基类。
    提供标准 CRUD 业务操作的通用实现，子类只需：
        1. 定义 entity_type 类属性（用于审计日志和日志输出）
        2. 实现 _to_response() 方法（Entity → DTO 转换）
        3. 可选覆盖 create/update/delete 方法添加业务校验

    Attributes:
        entity_type: 实体类型标识（如 "user", "role"），用于审计日志
        _repository: Repository 实例，由子类在 __init__ 中赋值

    Example:
        class UserService(BaseService[UserResponse, int, UserRepository]):
            entity_type = "user"
            def __init__(self, user_repository: UserRepository):
                self._repository = user_repository
            def _to_response(self, entity: UserEntity) -> UserResponse:
                return UserResponse.model_validate(entity)
    """

    entity_type: str = "unknown"  # 子类必须覆盖
    _repository: RepoType  # 子类在 __init__ 中赋值

    # ----------------------------------------------------------
    # 抽象方法（子类必须实现）
    # ----------------------------------------------------------
    @abstractmethod
    def _to_response(self, entity: Any) -> T:
        """将实体对象转换为响应 DTO。
        这是 Entity → DTO 的唯一转换点，确保数据格式统一。

        Args:
            entity: Repository 返回的实体对象

        Returns:
            T: 响应 DTO 对象
        """

    # ----------------------------------------------------------
    # 通用查询实现
    # ----------------------------------------------------------

    def get_by_id(self, id: ID) -> T | None:
        """根据主键查询实体。

        Args:
            id: 实体主键

        Returns:
            T | None: 查询到的 DTO，不存在时返回 None
        """
        entity = self._repository.get_by_id(id)
        return self._to_response(entity) if entity else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """分页查询所有实体。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            dict: 包含 items, total, page, page_size 的分页结果
        """
        skip = (page - 1) * page_size
        entities = self._repository.get_all(skip=skip, limit=page_size)
        total = self._repository.count()
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ----------------------------------------------------------
    # 通用写操作实现（子类通常需要覆盖以添加业务校验）
    # ----------------------------------------------------------

    def create(self, data: dict[str, Any], operator: dict[str, Any] | None = None) -> T:
        """创建实体。
        默认实现直接创建实体，子类应覆盖此方法添加：
            - 请求参数校验（如 Pydantic Request 模型）
            - 业务规则校验（如唯一性检查）
            - 密码哈希等数据转换

        Args:
            data: 创建数据（字典格式）
            operator: 操作者信息（用于审计日志）

        Returns:
            T: 创建成功的 DTO
        """
        raise NotImplementedError("子类必须覆盖 create 方法")

    def update(self, id: ID, data: dict[str, Any], operator: dict[str, Any] | None = None) -> T:
        """更新实体。
        默认实现直接更新实体，子类应覆盖此方法添加：
            - 请求参数校验
            - 业务规则校验（如唯一性检查、权限校验）
            - 部分更新逻辑（exclude_unset）

        Args:
            id: 实体主键
            data: 更新数据（字典格式）
            operator: 操作者信息（用于审计日志）

        Returns:
            T: 更新成功的 DTO
        """
        raise NotImplementedError("子类必须覆盖 update 方法")

    def delete(self, id: ID, operator: dict[str, Any] | None = None) -> bool:
        """删除实体（软删除）。
        默认实现直接删除，子类应覆盖此方法添加：
            - 存在性检查
            - 级联删除逻辑
            - 删除前的数据快照（用于审计）

        Args:
            id: 实体主键
            operator: 操作者信息（用于审计日志）

        Returns:
            bool: 是否删除成功
        """
        raise NotImplementedError("子类必须覆盖 delete 方法")

    # ----------------------------------------------------------
    # 通用工具方法（子类直接调用）
    # ----------------------------------------------------------

    def _commit(self) -> None:
        """提交当前数据库事务。
        统一的事务提交逻辑，失败时自动回滚并抛出异常。
        子类在 create/update/delete 中调用此方法。
        测试用的内存 Repository 没有 SQLAlchemy session，此方法安全跳过。

        Raises:
            Exception: 数据库操作失败时抛出原始异常
        """
        commit = getattr(self._repository, "commit", None)
        if commit is None:
            return
        try:
            commit()
        except Exception as e:
            session = getattr(self._repository, "session", None)
            if session is not None and hasattr(session, "rollback"):
                session.rollback()
            logger.error(f"[{self.entity_type}] 事务提交失败: {e}")
            raise

    def _audit(
        self,
        entity_id: Any,
        action: str,
        operator: dict[str, Any] | None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        remarks: str | None = None,
    ) -> None:
        """记录审计日志。
        调用 AuditService 记录数据变更，失败不影响主流程。

        Args:
            entity_id: 实体主键
            action: 操作类型（create/update/delete）
            operator: 操作者信息（包含 operator_id, ip_address）
            before_data: 变更前数据快照
            after_data: 变更后数据快照
            remarks: 备注说明
        """
        try:
            from src.services.admin.audit_service import AuditService

            AuditService().log_event(
                entity_type=self.entity_type,
                entity_id=entity_id,
                action=action,
                operator_id=operator.get("operator_id") if operator else None,
                before_data=before_data,
                after_data=after_data,
                ip_address=operator.get("ip_address") if operator else None,
                remarks=remarks or f"{self.entity_type} {action}",
            )
        except Exception as e:
            # 审计日志失败不影响主业务流程
            logger.warning(f"[{self.entity_type}] 审计日志写入失败: {e}")

    def _log_action(self, action: str, entity_id: Any, **kwargs: Any) -> None:
        """记录业务操作日志。

        Args:
            action: 操作类型
            entity_id: 实体主键
            **kwargs: 额外日志字段
        """
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"[{self.entity_type}] {action}: id={entity_id} {extra}")
