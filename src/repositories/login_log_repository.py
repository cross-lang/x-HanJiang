#!/usr/bin/env python3
"""
登录日志数据访问实现

本模块提供登录日志 Repository 的 SQLAlchemy 数据库实现。
支持按用户、登录结果、时间范围等条件查询（登录日志为只读流水，不提供更新/删除）。

分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    LoginLogRepository: 登录日志数据访问 SQLAlchemy 实现
"""

from datetime import datetime

from sqlalchemy import select

from src.core.exceptions import DatabaseException
from src.models.entities.log_entity import LoginLogEntity
from src.repositories.base_repository import BaseRepository


class LoginLogRepository(BaseRepository[LoginLogEntity, int]):
    """登录日志数据访问 SQLAlchemy 实现。"""

    model_class = LoginLogEntity

    def _base_query(self):
        """默认按创建时间倒序。"""
        return select(LoginLogEntity).order_by(LoginLogEntity.created_at.desc())

    # ── 业务查询 ──────────────────────────────────────────

    def search(
        self,
        user_id: int | None = None,
        status: str | None = None,
        login_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[LoginLogEntity], int]:
        """按条件搜索登录日志（分页）。"""
        conditions = []
        if user_id is not None:
            conditions.append(LoginLogEntity.user_id == user_id)
        if status:
            conditions.append(LoginLogEntity.status == status)
        if login_type:
            conditions.append(LoginLogEntity.login_type == login_type)
        if start_time is not None:
            conditions.append(LoginLogEntity.created_at >= start_time)
        if end_time is not None:
            conditions.append(LoginLogEntity.created_at <= end_time)
        return self._paginate(conditions, skip, limit)

    def update(self, id: int, entity: LoginLogEntity) -> LoginLogEntity | None:
        """登录日志不可变更，仅回读。"""
        return self.get_by_id(id)

    def delete(self, id: int) -> bool:
        """登录日志通常不开放删除。"""
        raise DatabaseException(message="登录日志不支持删除")
