"""create system_notifications

Revision ID: 0006_create_system_notifications
Revises: 0005_create_openapi_apps
Create Date: 2026-09-28 10:00:00.000000

系统通知（广播通知）表：管理员面向全体用户发布的普通通知与系统维护通知，
支持发布后撤回，是通知管理页面发布/撤回/列表/详情的数据载体。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_create_system_notifications"
down_revision = "0005_create_openapi_apps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_notifications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("title", sa.String(200), nullable=False, comment="通知标题"),
        sa.Column("content", sa.Text(), nullable=False, comment="通知正文"),
        sa.Column("notice_type", sa.String(32), nullable=False, comment="通知类型（notice/maintenance）"),
        sa.Column("maintenance_time", sa.String(50), nullable=True, comment="维护开始时间"),
        sa.Column("duration", sa.String(50), nullable=True, comment="预计持续时长"),
        sa.Column("reason", sa.String(500), nullable=True, comment="维护原因"),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="published",
            comment="发布状态（published/withdrawn）",
        ),
        sa.Column("operator_id", sa.BigInteger(), nullable=True, comment="操作人用户ID"),
        sa.Column("operator_name", sa.String(100), nullable=True, comment="操作人用户名"),
        sa.Column("published_at", sa.DateTime(), nullable=True, comment="发布时间"),
        sa.Column("withdrawn_at", sa.DateTime(), nullable=True, comment="撤回时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_notice_type", "system_notifications", ["notice_type"])
    op.create_index("idx_notice_status", "system_notifications", ["status"])
    op.create_index("idx_notice_created_at", "system_notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_notice_created_at", table_name="system_notifications")
    op.drop_index("idx_notice_status", table_name="system_notifications")
    op.drop_index("idx_notice_type", table_name="system_notifications")
    op.drop_table("system_notifications")
