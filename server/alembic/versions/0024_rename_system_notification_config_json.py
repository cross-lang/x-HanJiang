#!/usr/bin/env python3
"""system_notification_configs.config_json 更名 config，类型 TEXT 改为 JSON。

Revision ID: 0024_rename_system_notification_config_json
Revises: 0023_drop_notification_recipients
Create Date: 2026-10-06

变更内容：
- 字段 config_json 更名为 config（渠道配置对象，webhook 地址、密钥等）；
- 字段类型由 TEXT 改为 JSON，ORM 读取直接得到 Python dict。

说明：存量 TEXT 内容为 JSON 文本（seed 阶段以 json.dumps 写入），
脚本先对非法 JSON 文本置空对象，避免 MODIFY 时报 Invalid JSON text。
MySQL 非事务 DDL，中断后重跑可安全继续。
"""

import sqlalchemy as sa
from alembic import op

revision = "0024_rename_system_notification_config_json"
down_revision = "0023_drop_notification_recipients"
branch_labels = None
depends_on = None

_TABLE = "system_notification_configs"


def upgrade() -> None:
    # 1. 存量非法 JSON 文本置空对象（幂等）
    bind = op.get_bind()
    bind.exec_driver_sql(
        f"UPDATE `{_TABLE}` SET `config_json` = '{{}}' WHERE JSON_VALID(`config_json`) = 0"
    )
    # 2. 列更名 + 类型 TEXT → JSON
    op.alter_column(
        _TABLE,
        "config_json",
        new_column_name="config",
        existing_type=sa.Text(),
        type_=sa.JSON(),
        existing_nullable=False,
        comment="渠道配置对象，如webhook地址、密钥等",
    )


def downgrade() -> None:
    # 列更名回退 + 类型 JSON → TEXT（JSON 值由 MySQL 序列化为文本）
    op.alter_column(
        _TABLE,
        "config",
        new_column_name="config_json",
        existing_type=sa.JSON(),
        type_=sa.Text(),
        existing_nullable=False,
        comment="渠道配置JSON，如webhook地址、密钥等",
    )
