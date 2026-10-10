#!/usr/bin/env python3
"""
数据库基础设施模块
本模块提供数据库连接池管理和会话工厂，确保数据库连接的高效复用和生命周期管理。
功能特性：
    - 基于 SQLAlchemy 2.0 的同步支持
    - MySQL 连接池管理和配置
    - 上下文管理器确保会话自动关闭

Usage:
    from src.infras.database import get_cached_database_provider, Base
    provider = get_cached_database_provider()
    with provider.session() as session:
        result = session.execute(select(User))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import settings
from src.core.logger import logger
from src.utils.helpers import mask_url_credentials


class Base(DeclarativeBase):
    """ORM 声明式基类（SQLAlchemy 2.0 风格，mypy 可识别）。"""


# ============================================================
# 抽象基类
# ============================================================
class DatabaseProvider(ABC):
    """数据库提供者抽象接口。
    所有数据库后端必须实现此接口。业务层仅依赖此抽象，
    切换数据库实现只需修改配置，无需改动任何业务代码。
    """

    @abstractmethod
    def get_engine(self) -> Engine:
        """获取数据库引擎。"""

    @abstractmethod
    def get_session_factory(self) -> sessionmaker[Session]:
        """获取会话工厂。"""

    @abstractmethod
    @contextmanager
    def session(self) -> Iterator[Session]:
        """获取数据库会话的上下文管理器。"""

    @abstractmethod
    def check_connection(self) -> bool:
        """检测数据库连接是否可用。"""

    @abstractmethod
    def close(self) -> None:
        """关闭数据库连接，释放资源。"""


# ============================================================

# MySQL (SQLAlchemy) 实现

# ============================================================


class MySqlProvider(DatabaseProvider):
    """MySQL 数据库实现（基于 SQLAlchemy）。"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 3600,
        echo: bool = False,
    ) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL 配置不能为空，请在配置文件或环境变量中设置")
        if database_url.startswith("mysql://"):
            database_url = database_url.replace("mysql://", "mysql+pymysql://")
        self._engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            echo=echo,
            # 统一存储北京时间（UTC+8）：MySQL 系统时区为 UTC，
            # 不设置时区时 CURRENT_TIMESTAMP 默认值会落 UTC，比本地早 8 小时。
            connect_args={"init_command": "SET time_zone = '+08:00'"},
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info(f"MySqlProvider initialized: {mask_url_credentials(database_url)}")

    def get_engine(self) -> Engine:
        return self._engine

    def get_session_factory(self) -> sessionmaker[Session]:
        return self._session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        """获取数据库会话的上下文管理器。"""
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"MySQL operation failed, rolled back: {e}")
            raise
        finally:
            session.close()

    def check_connection(self) -> bool:
        """检测数据库连接是否可用。"""
        try:
            with self._engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Database connection check failed: {e}")
            return False

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
            logger.info("MySQL connection closed")


# ============================================================

# 工厂函数

# ============================================================


def get_database_provider() -> DatabaseProvider:
    """根据配置创建数据库提供者实例。"""
    return MySqlProvider(
        database_url=settings.database.url,
        pool_size=settings.database.pool_size,
        echo=settings.server.debug,
    )


# 模块级缓存实例

_db_provider: DatabaseProvider | None = None


def get_cached_database_provider() -> DatabaseProvider:
    """获取缓存的数据库提供者（应用级别单例）。"""
    global _db_provider
    if _db_provider is None:
        _db_provider = get_database_provider()
    return _db_provider


# ============================================================
# 启动期进程级互斥锁（MySQL GET_LOCK）
# ============================================================


def acquire_mysql_lock(session: Session, lock_name: str, timeout: int = 60) -> bool:
    """获取 MySQL 命名锁（GET_LOCK），用于串行化启动期数据初始化。

    背景：gunicorn 多 worker 各自执行 ASGI lifespan，seed / 权限对账 /
    scope 对账会在多个进程中并发运行，唯一键（uk_perm_code 等）并发
    插入必然产生 1062 Duplicate entry 竞态。命名锁保证同一时刻只有一个
    worker 执行初始化，其余 worker 等待或跳过。

    Args:
        session: 当前数据库会话（锁与连接绑定，必须在同一会话上释放）
        lock_name: 锁名（如 "hanjiang.seed"）
        timeout: 等待锁的超时秒数

    Returns:
        True 表示成功获取锁；False 表示超时未获取（调用方应跳过初始化）
    """
    conn = session.connection()
    acquired = conn.execute(text(f"SELECT GET_LOCK('{lock_name}', {timeout})")).scalar()
    return bool(acquired)


def release_mysql_lock(session: Session, lock_name: str) -> None:
    """释放 MySQL 命名锁（RELEASE_LOCK），须与 acquire_mysql_lock 成对调用。"""
    session.connection().execute(text(f"SELECT RELEASE_LOCK('{lock_name}')"))


def init_db() -> None:
    """初始化 MySQL 数据库，创建所有表。"""
    from src.models import entities  # noqa: F401

    engine = get_cached_database_provider().get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("MySQL tables created")


def drop_db() -> None:
    """删除所有 MySQL 数据库表。"""
    engine = get_cached_database_provider().get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("All MySQL tables dropped")


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个数据库会话，请求结束自动 commit/rollback/close。"""
    session = get_cached_database_provider().get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "DatabaseProvider",
    "MySqlProvider",
    "Base",
    "get_database_provider",
    "get_cached_database_provider",
    "get_db_session",
    "init_db",
    "drop_db",
]
