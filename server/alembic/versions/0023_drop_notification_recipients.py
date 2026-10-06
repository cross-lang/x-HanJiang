#!/usr/bin/env python3
"""删除通知接收人表，user_notification_configs.recipient 改为 JSON 数组。

Revision ID: 0023_drop_notification_recipients
Revises: 0022_add_registration_code
Create Date: 2026-10-06

变更内容：
- 删除 user_notification_recipients 表（其多接收人能力并入
  user_notification_configs.recipient JSON 数组）；
- user_notification_configs.recipient 由 VARCHAR(256) 改为 JSON，
  存储格式 [{"recipient":"xxx@qq.com","label":"私人邮箱","enabled":1}]；
- 存量纯字符串数据先转换为 JSON 数组，避免 MODIFY 时报 Invalid JSON text。

说明：user_notification_recipients 由 ORM create_all 自动建表、未进迁移历史，
脚本对"表已存在"做幂等保护；MySQL 非事务 DDL，中断后重跑可安全继续。
"""

import sqlalchemy as sa
from alembic import op

revision = "0023_drop_notification_recipients"
down_revision = "0022_add_registration_code"
branch_labels = None
depends_on = None

_TABLE = "user_notification_configs"
_COLUMN = "recipient"


def _has_table(bind: sa.engine.Connection, table: str) -> bool:
    """判断数据库中是否已存在指定表。"""
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    # 1. 删除通知接收人表（如存在，兼容 create_all 自动建表的历史库）
    bind = op.get_bind()
    if _has_table(bind, "user_notification_recipients"):
        op.drop_table("user_notification_recipients")
    # 2. 存量纯字符串接收人先转换为 JSON 数组（幂等：仅处理非 JSON 值）
    # 表名/列名为脚本内常量，非外部输入，无注入风险。
    bind.exec_driver_sql(
        f"UPDATE `{_TABLE}` SET `{_COLUMN}` = JSON_ARRAY("
        f"JSON_OBJECT('recipient', `{_COLUMN}`, 'label', '', 'enabled', 1)) "
        f"WHERE JSON_VALID(`{_COLUMN}`) = 0"
    )
    # 3. 列类型 VARCHAR → JSON
    op.alter_column(
        _TABLE,
        _COLUMN,
        existing_type=sa.String(length=256),
        type_=sa.JSON(),
        existing_nullable=False,
        comment="渠道接收人列表 JSON，如 [{\"recipient\":\"a@b.com\",\"label\":\"私人邮箱\",\"enabled\":1}]",
    )


def downgrade() -> None:
    # 1. 列类型 JSON → VARCHAR（JSON 对象序列化为文本字符串）
    op.alter_column(
        _TABLE,
        _COLUMN,
        existing_type=sa.JSON(),
        type_=sa.String(length=256),
        existing_nullable=False,
        comment="渠道接收人标识",
    )
    # 2. 重建通知接收人表
    op.create_table(
        "user_notification_recipients",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=True, comment="用户ID，NULL=系统级接收人"),
        sa.Column("channel", sa.String(length=32), nullable=False, comment="通知渠道"),
        sa.Column("recipient", sa.String(length=256), nullable=False, comment="接收人地址"),
        sa.Column("label", sa.String(length=64), nullable=False, server_default="", comment="备注标签"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
