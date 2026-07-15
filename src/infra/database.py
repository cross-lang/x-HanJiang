#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库基础设施模块

本模块提供数据库连接池管理和会话工厂，确保数据库连接的高效复用和生命周期管理。
支持 MySQL 数据库，使用连接池提升性能。

功能特性：
    - 基于 SQLAlchemy 2.0 的同步支持
    - 连接池管理和配置
    - 上下文管理器确保会话自动关闭
    - 通用事务封装（不含单表业务CRUD）
    - 支持多环境配置

Usage:
    from src.infra.database import get_db, engine, Base, transaction

    # 获取数据库会话
    with get_db() as session:
        result = session.execute(select(User))

    # 使用事务装饰器
    @transaction
    def create_user(session: Session, data: dict) -> User:
        ...
"""

from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.core.config import settings
from src.core.logger import logger

Base = declarative_base()

_engine: Engine | None = None
_session_factory: sessionmaker | None = None

T = TypeVar("T")


def get_engine() -> Engine:
    """获取数据库引擎单例。

    Returns:
        Engine: SQLAlchemy 数据库引擎

    Raises:
        ValueError: DATABASE_URL 配置为空时抛出
    """
    global _engine, _session_factory

    if _engine is None:
        database_url: str = settings.database.url
        if not database_url:
            raise ValueError("DATABASE_URL 配置不能为空，请在配置文件或环境变量中设置")

        if database_url.startswith("mysql://"):
            database_url = database_url.replace("mysql://", "mysql+pymysql://")

        _engine = create_engine(
            database_url,
            pool_size=settings.database.pool_size,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.server.debug,
        )

        _session_factory = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        logger.info(f"Database engine initialized: {database_url}")

    return _engine


def get_session_factory() -> sessionmaker:
    """获取会话工厂单例。

    Returns:
        sessionmaker: SQLAlchemy 会话工厂
    """
    global _session_factory

    if _session_factory is None:
        get_engine()

    return _session_factory


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的上下文管理器。

    使用方式：
        with get_db() as session:
            user = session.query(User).first()

    Yields:
        Session: 数据库会话对象

    Raises:
        Exception: 数据库操作异常时自动回滚并重新抛出
    """
    session_factory: sessionmaker = get_session_factory()
    session: Session = session_factory()

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database operation failed, rolled back: {e}")
        raise
    finally:
        session.close()


def transaction(func: Callable[..., T]) -> Callable[..., T]:
    """事务装饰器。

    为函数提供数据库事务支持，自动管理事务的提交和回滚。
    被装饰的函数必须接受 Session 作为第一个参数。

    Usage:
        @transaction
        def create_order(session: Session, data: dict) -> Order:
            order = Order(**data)
            session.add(order)
            return order

    Args:
        func: 需要事务支持的函数

    Returns:
        Callable: 包装后的函数，自动处理事务
    """

    def wrapper(session: Session, *args: Any, **kwargs: Any) -> T:
        try:
            result: T = func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed, rolled back: {func.__name__}, error: {e}")
            raise

    return wrapper


def init_db() -> None:
    """初始化数据库，创建所有表。

    注意：生产环境建议使用数据库迁移工具（如 Alembic）管理表结构变更。
    """
    engine: Engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_db() -> None:
    """删除所有数据库表。

    注意：此操作不可逆，仅用于测试环境或开发环境。
    """
    engine: Engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


def close_db() -> None:
    """关闭数据库连接，清理资源。"""
    global _engine, _session_factory

    if _engine:
        _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection closed")


__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "get_db",
    "transaction",
    "init_db",
    "drop_db",
    "close_db",
]