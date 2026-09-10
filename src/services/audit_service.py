#!/usr/bin/env python3
"""
审计日志业务逻辑实现

提供审计日志记录（写）与查询（读）能力。
审计写入失败不应阻断主业务流程，由调用方决定是否吞掉异常。

Classes:
    AuditService: 审计日志业务逻辑实现
"""

from datetime import datetime
from typing import Any

from src.core.exceptions import NotFoundException
from src.core.logger import logger
from src.models.entities.log_entity import AuditLogEntity
from src.repositories.log_repository import AuditLogRepository, LoginLogRepository
from src.schemas.audit import AuditLogResponse, LoginLogResponse
from src.services.base_service import BaseService


class AuditService(BaseService[AuditLogResponse, int]):
    """审计日志业务逻辑实现。

    Attributes:
        _repository: 审计日志数据访问实例
        _login_log_repository: 登录日志数据访问实例
    """

    def __init__(
        self,
        audit_log_repository: AuditLogRepository,
        login_log_repository: LoginLogRepository | None = None,
    ) -> None:
        """初始化审计服务。"""
        self._repository: AuditLogRepository = audit_log_repository
        self._login_log_repository = login_log_repository or LoginLogRepository(
            session=audit_log_repository.session
        )

    def log(
        self,
        tenant_id: int | None,
        user_id: int | None,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        detail: str | None = None,
        scope: str | None = None,
        result: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLogResponse:
        """记录一条审计日志。

        Args:
            tenant_id: 租户ID
            user_id: 操作用户ID
            action: 操作动作（create/update/delete/login 等）
            resource_type: 资源类型（user/role/tenant/workspace 等）
            resource_id: 资源ID
            detail: 操作详情描述
            scope: 授权范围（如 read:anonymized、read:export）
            result: 操作结果（success/need_approval/failed）
            ip_address: 客户端IP
            user_agent: 客户端 User-Agent

        Returns:
            AuditLogResponse: 写入成功的日志响应

        Raises:
            MysqlException: 数据库写入失败时抛出
        """
        entity = AuditLogEntity(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            scope=scope,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        created = self._repository.create(entity)
        if self._repository.session is not None:
            self._repository.session.commit()
        logger.info(
            f"Audit log: user={user_id} action={action} "
            f"resource={resource_type}#{resource_id}"
        )
        return self._to_response(created, username=None)

    def get_by_id(self, id: int) -> AuditLogResponse | None:
        """根据 ID 查询审计日志。"""
        entity = self._repository.get_by_id(id)
        if entity is None:
            return None
        return self._to_response(entity, username=None)

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询所有审计日志（分页）。"""
        skip = (page - 1) * page_size
        rows, total = self._repository.search(skip=skip, limit=page_size)
        return {
            "items": [self._to_response(e, username) for e, username in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def search(
        self,
        tenant_id: int | None = None,
        user_id: int | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索审计日志（分页）。

        Args:
            tenant_id: 租户过滤
            user_id: 用户过滤
            action: 操作动作过滤
            resource_type: 资源类型过滤
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页记录数

        Returns:
            dict: 分页结果
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.search(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_response(e, username) for e, username in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def search_login_logs(
        self,
        tenant_id: int | None = None,
        user_id: int | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索登录日志（分页）。

        Args:
            tenant_id: 租户过滤
            user_id: 用户过滤
            status: 登录结果过滤（success/failed）
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页记录数

        Returns:
            dict: 分页结果

        Raises:
            NotFoundException: 日志不存在时抛出（占位，当前实现恒不触发）
        """
        skip = (page - 1) * page_size
        rows, total = self._login_log_repository.search(
            tenant_id=tenant_id,
            user_id=user_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_login_response(e, username) for e, username in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _to_response(
        self, entity: AuditLogEntity, username: str | None
    ) -> AuditLogResponse:
        """实体转响应 DTO。"""
        return AuditLogResponse(
            id=entity.id,
            tenant_id=entity.tenant_id,
            user_id=entity.user_id,
            username=username,
            action=entity.action,
            resource_type=entity.resource_type,
            resource_id=entity.resource_id,
            detail=entity.detail,
            scope=entity.scope,
            result=entity.result,
            ip_address=entity.ip_address,
            user_agent=entity.user_agent,
            created_at=entity.created_at,
        )

    def _to_login_response(
        self, entity: object, username: str | None
    ) -> LoginLogResponse:
        """登录日志实体转响应 DTO。"""
        return LoginLogResponse(
            id=entity.id,  # type: ignore[attr-defined]
            tenant_id=entity.tenant_id,  # type: ignore[attr-defined]
            user_id=entity.user_id,  # type: ignore[attr-defined]
            username=username,
            login_type=entity.login_type.value if entity.login_type else "password",  # type: ignore[attr-defined]
            ip_address=entity.ip_address,  # type: ignore[attr-defined]
            status=entity.status.value if entity.status else "success",  # type: ignore[attr-defined]
            created_at=entity.created_at,  # type: ignore[attr-defined]
        )
