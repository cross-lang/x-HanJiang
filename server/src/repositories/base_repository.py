#!/usr/bin/env python3
"""
数据访问层基类

提供基于 SQLAlchemy 的通用 CRUD 默认实现，子类只需：
  1. 设置 model_class 类属性
  2. 可选覆盖 _base_query() 添加默认过滤条件（如软删除过滤、默认排序）
  3. 可选覆盖 _handle_integrity_error() 自定义唯一约束异常处理
  4. 扩展业务查询方法，使用 _paginate() 统一分页

类型参数：
    T: 实体类型（ORM 模型，例如 SQLAlchemy declarative class）
    ID: 主键类型

Classes:
    BaseRepository: 数据访问层基类（模板方法模式）
"""

from __future__ import annotations

from abc import ABC
from typing import ClassVar, Generic, TypeVar

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from src.core.exceptions import ConflictException, DatabaseException
from src.infras.database import get_cached_database_provider

T = TypeVar("T")
ID = TypeVar("ID")


class BaseRepository(ABC, Generic[T, ID]):
    """数据访问层基类。

    提供通用 CRUD 默认实现，子类通过模板方法自定义行为。

    子类必须设置:
        model_class: ORM 实体类

    可选覆盖:
        _base_query(): 基础查询（添加默认过滤/排序）
        _handle_integrity_error(): 自定义唯一约束异常处理
    """

    model_class: ClassVar[type]

    def __init__(self, session: Session | None = None) -> None:
        """初始化 Repository。

        Args:
            session: SQLAlchemy 会话（可选，未提供时自动创建）
        """
        self.session: Session = (
            session or get_cached_database_provider().get_session_factory()()
        )

    # ── 查询 ──────────────────────────────────────────────

    def get_by_id(self, id: ID) -> T | None:
        """根据主键查询实体。"""
        stmt = self._base_query().where(self.model_class.id == id)
        return self.session.execute(stmt).scalars().first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """查询所有实体（分页）。"""
        stmt = self._base_query().offset(skip).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count(self) -> int:
        """统计实体总数。"""
        stmt = select(func.count()).select_from(self._base_query().subquery())
        return self.session.execute(stmt).scalar() or 0

    # ── 写入 ──────────────────────────────────────────────

    def create(self, entity: T) -> T:
        """创建新实体。"""
        try:
            self.session.add(entity)
            self.session.flush()
            return entity
        except IntegrityError as e:
            self.session.rollback()
            self._handle_integrity_error(e, entity)
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(
                message=f"创建{self._entity_name()}失败: {e}"
            ) from e

    def update(self, id: ID, entity: T) -> T | None:
        """更新实体。

        默认实现：反射复制非主键、非自动管理字段到已加载实体。
        子类可覆盖此方法自定义字段映射逻辑。
        """
        existing = self.get_by_id(id)
        if existing is None:
            return None

        columns = {c.key for c in inspect(self.model_class).columns} - {"id", "created_at"}
        for key in columns:
            value = getattr(entity, key, None)
            if value is not None:
                setattr(existing, key, value)

        try:
            self.session.flush()
            return existing
        except IntegrityError as e:
            self.session.rollback()
            self._handle_integrity_error(e, entity)
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(
                message=f"更新{self._entity_name()}失败: {e}"
            ) from e

    def delete(self, id: ID) -> bool:
        """删除实体。

        默认实现：物理删除。子类可覆盖为软删除。
        """
        existing = self.get_by_id(id)
        if existing is None:
            return False
        try:
            self.session.delete(existing)
            self.session.flush()
            return True
        except Exception as e:
            self.session.rollback()
            raise DatabaseException(
                message=f"删除{self._entity_name()}失败: {e}"
            ) from e

    # ── 分页辅助 ──────────────────────────────────────────

    def _paginate(
        self, conditions: list, skip: int = 0, limit: int = 100
    ) -> tuple[list[T], int]:
        """统一分页查询。

        Args:
            conditions: SQLAlchemy 过滤条件列表
            skip: 偏移量
            limit: 每页数量

        Returns:
            tuple[list[T], int]: (实体列表, 总数)
        """
        total = (
            self.session.execute(
                select(func.count()).select_from(
                    select(self.model_class).where(*conditions).subquery()
                )
            ).scalar()
            or 0
        )
        stmt = self._base_query().where(*conditions).offset(skip).limit(limit)
        rows = list(self.session.execute(stmt).scalars().all())
        return rows, total

    # ── 模板方法（子类可覆盖）──────────────────────────────

    def _base_query(self) -> Select:
        """基础查询。

        子类可覆盖以添加默认过滤条件（如 deleted_at IS NULL）
        或默认排序（如 created_at DESC）。
        """
        return select(self.model_class)

    def _handle_integrity_error(self, error: IntegrityError, entity: T) -> None:
        """唯一约束冲突处理。

        子类可覆盖以提供更友好的错误信息。
        默认抛出通用 ConflictException。
        """
        raise ConflictException(
            message=f"{self._entity_name()}数据冲突",
            details={"error": str(error.orig)},
        )

    # ── 内部工具 ──────────────────────────────────────────

    @staticmethod
    def _entity_name() -> str:
        """获取实体名称，子类可覆盖提供更友好的名称。"""
        return "实体"
