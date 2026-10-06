"""merge user_notification_preferences into user_notification_configs

Revision ID: 0028
Revises: 0027_simplify_system_notifications
Create Date: 2026-10-06

合并两张表：
1. user_notification_configs 增加 event_type 列；
2. recipient 由 JSON 数组改为单值 VARCHAR(512)；
3. 唯一索引由 (user_id, channel) 改为 (user_id, event_type, channel)；
4. 删除 user_notification_preferences 表。

注意：本项目为第一版，存量数据由用户自行清理，迁移不做 JSON 数组→单值的数据搬迁。
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027_simplify_system_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 删除旧唯一索引
    op.drop_index("uk_user_channel", table_name="user_notification_configs")

    # 2) 新增 event_type 列（先默认空串，存量数据由用户清理后重发）
    op.add_column(
        "user_notification_configs",
        sa.Column("event_type", sa.String(length=64), nullable=False, server_default="", comment="事件类型"),
    )

    # 3) recipient 由 JSON 改为单值 VARCHAR(512)
    op.alter_column(
        "user_notification_configs",
        "recipient",
        existing_type=sa.JSON(),
        type_=sa.String(length=512),
        nullable=False,
        server_default=sa.text("''"),
        comment="渠道接收方（单值；station 渠道为空串）",
    )

    # 4) 新唯一索引
    op.create_index(
        "uk_user_event_channel",
        "user_notification_configs",
        ["user_id", "event_type", "channel"],
        unique=True,
    )

    # 5) 删除旧 preferences 表
    op.drop_table("user_notification_preferences")


def downgrade() -> None:
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.drop_index("uk_user_event_channel", table_name="user_notification_configs")
    op.alter_column(
        "user_notification_configs",
        "recipient",
        existing_type=sa.String(length=512),
        type_=sa.JSON(),
        nullable=False,
    )
    op.drop_column("user_notification_configs", "event_type")
    op.create_index("uk_user_channel", "user_notification_configs", ["user_id", "channel"], unique=True)
