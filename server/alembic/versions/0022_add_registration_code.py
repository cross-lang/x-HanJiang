#!/usr/bin/env python3
"""为 openapi_app_registrations 新增申请码列并回填存量数据。

Revision ID: 0022_add_registration_code
Revises: 0021_create_app_registrations
Create Date: 2026-10-05

变更内容：
- 新增 registration_code（6 位数字申请码，对外展示用，替代申请ID展示）；
- 存量批次行以 Python 侧随机数回填并保证全局唯一；
- 追加唯一索引 uq_reg_code，防止申请码重复。

说明：MySQL 采用非事务 DDL，脚本对"列/索引已存在"场景做了幂等保护，
中断后重跑可安全继续（曾出现 add_column 已生效但迁移未标记完成的情况）。
"""

import random

import sqlalchemy as sa
from alembic import op

revision = "0022_add_registration_code"
down_revision = "0021_create_app_registrations"
branch_labels = None
depends_on = None

_TABLE = "openapi_app_registrations"
_COLUMN = "registration_code"


def _has_column(bind: sa.engine.Connection, column: str) -> bool:
    """判断表中是否已存在指定列。"""
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(_TABLE)}


def _existing_codes(bind: sa.engine.Connection) -> set[str]:
    """查询表中已存在的申请码集合。"""
    return {
        row[0]
        for row in bind.exec_driver_sql(
            f"SELECT `{_COLUMN}` FROM `{_TABLE}` WHERE `{_COLUMN}` IS NOT NULL"
        ).fetchall()
    }


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, _COLUMN):
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.String(6), nullable=True, comment="申请码：6位数字，对外展示用"),
        )
    # 为存量行回填唯一随机申请码（表通常较小，Python 循环足够；无 NULL 行时跳过）
    existing = _existing_codes(bind)
    rows = bind.exec_driver_sql(f"SELECT `id` FROM `{_TABLE}` WHERE `{_COLUMN}` IS NULL").fetchall()
    for (row_id,) in rows:
        code = f"{random.randint(100000, 999999)}"
        while code in existing:
            code = f"{random.randint(100000, 999999)}"
        existing.add(code)
        bind.exec_driver_sql(
            f"UPDATE `{_TABLE}` SET `{_COLUMN}` = %s WHERE `id` = %s",
            (code, row_id),
        )
    op.alter_column(_TABLE, _COLUMN, existing_type=sa.String(6), nullable=False)
    insp = sa.inspect(bind)
    if "uq_reg_code" not in {c["name"] for c in insp.get_unique_constraints(_TABLE)}:
        op.create_unique_constraint("uq_reg_code", _TABLE, [_COLUMN])


def downgrade() -> None:
    op.drop_constraint("uq_reg_code", _TABLE, type_="unique")
    op.drop_column(_TABLE, _COLUMN)
