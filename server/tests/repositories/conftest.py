#!/usr/bin/env python3
"""仓储层测试共用夹具：内存 SQLite + 真实建表。

不连接真实 MySQL，改用 SQLite 内存库执行真实 Repository 的 SQLAlchemy 查询，
从而覆盖仓储层的语句分支（查询/过滤/分页/软删/关联），而非用 FakeSession 假装。
StaticPool 保证内存库在同一连接上复用（否则每个 Session 都会得到空库）。
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# 导入实体模块以注册表元数据（本切片需要的表：认证 5 张 + 文件/审计/登录日志 3 张）
from src.infras.database import Base
from src.models.entities.audit_entity import AuditLogEntity
from src.models.entities.file_entity import FileEntity
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
    UserEntity,
    UserRoleEntity,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(element, compiler, **kw) -> str:  # noqa: ANN001
    """SQLite 下把 BigInteger 主键编译为 INTEGER，使其成为 rowid 别名从而自增。

    MySQL 的 BIGINT 主键自增，SQLite 仅 INTEGER PRIMARY KEY 才是 rowid 别名。
    此钩子仅作用于测试用 SQLite 方言，不影响生产 MySQL DDL。
    """
    return "INTEGER"


# 本切片只需要这些表；刻意只建它们，避免 Base.metadata 中其他表
# （如 openapi_scopes）与 permissions 表存在同名索引 idx_module 而在 SQLite 建表时冲突。
# files / audit_logs / login_logs 不含 idx_module，可安全加入。
_AUTH_TABLES = [
    UserEntity.__table__,
    RoleEntity.__table__,
    PermissionEntity.__table__,
    RolePermissionEntity.__table__,
    UserRoleEntity.__table__,
    FileEntity.__table__,
    AuditLogEntity.__table__,
    LoginLogEntity.__table__,
]


# UserRoleEntity 与 LoginLogEntity 都定义了同名索引 idx_user_id；
# SQLite 要求索引名在整个库内唯一，故建表前移除 login_logs 上的该索引
# （索引仅用于性能，不影响仓储查询的正确性）。
for _idx in list(LoginLogEntity.__table__.indexes):
    if _idx.name == "idx_user_id":
        LoginLogEntity.__table__.indexes.discard(_idx)


@pytest.fixture
def db_session() -> Iterator[Session]:
    """创建内存 SQLite 引擎、建表并返回一个绑定连接的 Session。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=_AUTH_TABLES)
    connection = engine.connect()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        connection.close()
        engine.dispose()
