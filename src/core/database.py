#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接管理模块

本模块提供数据库连接池管理和会话工厂，确保数据库连接的高效复用和生命周期管理。
支持 MySQL 数据库，使用连接池提升性能。

功能特性：
    - 基于 SQLAlchemy 2.0 的异步支持
    - 连接池管理和配置
    - 上下文管理器确保会话自动关闭
    - 支持多环境配置

Usage:
    from src.core.database import get_db, engine, Base

    # 获取数据库会话
    async with get_db() as session:
        result = await session.execute(select(User))
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.core.config import settings

# 创建数据库引擎
_engine: Engine | None = None

# 创建会话工厂
_session_factory: sessionmaker | None = None

# 声明基类，所有 ORM 模型都应继承此类
Base = declarative_base()


def get_engine() -> Engine:
    """获取数据库引擎单例。

    Returns:
        Engine: SQLAlchemy 数据库引擎
    """
    global _engine, _session_factory

    if _engine is None:
        database_url: str = settings.database.DATABASE_URL
        if not database_url:
            raise ValueError("DATABASE_URL 配置不能为空，请在配置文件或环境变量中设置")

        # 转换 pymysql 连接字符串为 SQLAlchemy 兼容格式
        if database_url.startswith("mysql://"):
            database_url = database_url.replace("mysql://", "mysql+pymysql://")

        _engine = create_engine(
            database_url,
            pool_size=settings.database.DATABASE_POOL_SIZE,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.server.SERVER_DEBUG,
        )

        # 创建会话工厂
        _session_factory = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    return _engine


def get_session_factory() -> sessionmaker:
    """获取会话工厂单例。

    Returns:
        sessionmaker: SQLAlchemy 会话工厂
    """
    global _session_factory

    if _session_factory is None:
        get_engine()  # 确保引擎已创建

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
        Exception: 数据库操作异常
    """
    session_factory: sessionmaker = get_session_factory()
    session: Session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """初始化数据库，创建所有表。

    注意：生产环境建议使用数据库迁移工具（如 Alembic）管理表结构变更。
    """
    engine: Engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """删除所有数据库表。

    注意：此操作不可逆，仅用于测试环境或开发环境。
    """
    engine: Engine = get_engine()
    Base.metadata.drop_all(bind=engine)


def close_db() -> None:
    """关闭数据库连接，清理资源。"""
    global _engine, _session_factory

    if _engine:
        _engine.dispose()
        _engine = None
        _session_factory = None


# 导出公共接口
__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "get_db",
    "init_db",
    "drop_db",
    "close_db",
]
