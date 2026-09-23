"""create notification_records table

Revision ID: 0002_create_notification_records
Revises: 0001_create_user
Create Date: 2026-09-23 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_create_notification_records"
down_revision = "0001_create_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("event_type", sa.String(length=64), nullable=False, comment="事件类型"),
        sa.Column("channel", sa.String(length=32), nullable=False, comment="发送渠道"),
        sa.Column("recipient", sa.String(length=256), nullable=False, comment="接收人"),
        sa.Column("subject", sa.String(length=512), nullable=False, server_default="", comment="通知主题"),
        sa.Column("content", sa.Text(), nullable=False, comment="渲染后正文"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", comment="发送状态"),
        sa.Column("retry_count", sa.BigInteger(), nullable=False, server_default=sa.text("0"), comment="已重试次数"),
        sa.Column("max_retries", sa.BigInteger(), nullable=False, server_default=sa.text("3"), comment="最大重试次数"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("metadata_json", sa.Text(), nullable=True, comment="扩展元数据 JSON"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True, comment="发送时间"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("idx_event_type", "notification_records", ["event_type"])
    op.create_index("idx_channel", "notification_records", ["channel"])
    op.create_index("idx_status", "notification_records", ["status"])
    op.create_index("idx_status_retry", "notification_records", ["status", "retry_count"])
    op.create_index("idx_created_at", "notification_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_created_at", table_name="notification_records")
    op.drop_index("idx_status_retry", table_name="notification_records")
    op.drop_index("idx_status", table_name="notification_records")
    op.drop_index("idx_channel", table_name="notification_records")
    op.drop_index("idx_event_type", table_name="notification_records")
    op.drop_table("notification_records")
