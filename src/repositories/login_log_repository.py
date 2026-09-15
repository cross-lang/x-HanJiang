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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import DatabaseException
from src.infras.database import get_cached_database_provider
from src.models.entities.log_entity import LoginLogEntity
from src.repositories.base_repository import BaseRepository


class LoginLogRepository(BaseRepository[LoginLogEntity, int]):
    """登录日志数据访问 SQLAlchemy 实现。

    Attributes:
        session: 数据库会话对象
    """

    def __init__(self, session: Session | None = None) -> None:
        """初始化登录日志仓库。"""
        self.session: Session = session or get_cached_database_provider().get_session_factory()()

    def get_by_id(self, id: int) -> LoginLogEntity | None:
        """根据日志 ID 查询登录日志。"""
        stmt = select(LoginLogEntity).where(LoginLogEntity.id == id)
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[LoginLogEntity]:
        """查询全部登录日志（分页，按时间倒序）。"""
        stmt = (
            select(LoginLogEntity)
            .order_by(LoginLogEntity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        """统计登录日志总数。"""
        stmt = select(func.count()).select_from(LoginLogEntity)
        return self.session.execute(stmt).scalar() or 0

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
        """按条件搜索登录日志（分页，按时间倒序）。"""
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

        base = select(LoginLogEntity).where(*conditions).order_by(
            LoginLogEntity.created_at.desc()
        )
        total = (
            self.session.execute(
                select(func.count()).select_from(base.subquery())
            ).scalar()
            or 0
        )
        rows = self.session.execute(base.offset(skip).limit(limit)).scalars().all()
        return list(rows), total

    def create(self, entity: LoginLogEntity) -> LoginLogEntity:
        """写入一条登录日志。"""
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"写入登录日志失败: {e}") from e

    def update(self, id: int, entity: LoginLogEntity) -> LoginLogEntity | None:
        """更新登录日志（基类接口，登录日志不可变更）。"""
        return self.get_by_id(id)

    def delete(self, id: int) -> bool:
        """删除登录日志（基类接口，通常不开放）。"""
        existing = self.get_by_id(id)
        if existing is None:
            return False
        try:
            self.session.delete(existing)
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(message=f"删除登录日志失败: {e}") from e

    def count(self) -> int:
        """统计登录日志总数（BaseRepository 接口）。"""
        return self.count_all()
