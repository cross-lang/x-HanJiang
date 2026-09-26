"""create user_notification_configs table

Revision ID: 0003_create_user_notification_configs
Revises: 0002_create_notification_records
Create Date: 2026-09-23 16:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_create_user_notification_configs"
down_revision = "0002_create_notification_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_notification_configs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="用户ID"),
        sa.Column("channel", sa.String(length=32), nullable=False, comment="通知渠道"),
        sa.Column("recipient", sa.String(length=256), nullable=False, comment="渠道接收人标识"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("idx_user_id", "user_notification_configs", ["user_id"])
    op.create_index(
        "uk_user_channel",
        "user_notification_configs",
        ["user_id", "channel"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uk_user_channel", table_name="user_notification_configs")
    op.drop_index("idx_user_id", table_name="user_notification_configs")
    op.drop_table("user_notification_configs")
