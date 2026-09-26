"""create user table

Revision ID: 0001_create_user
Revises:
Create Date: 2026-07-30 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_create_user"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="用户唯一标识"),
        sa.Column("username", sa.String(length=50), nullable=False, comment="用户名"),
        sa.Column("email", sa.String(length=255), nullable=False, comment="邮箱地址"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="显示名称"),
        sa.Column("age", sa.Integer(), nullable=True, comment="年龄"),
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
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_user_username"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("idx_user_username", "user", ["username"])
    op.create_index("idx_user_email", "user", ["email"])


def downgrade() -> None:
    op.drop_index("idx_user_email", table_name="user")
    op.drop_index("idx_user_username", table_name="user")
    op.drop_table("user")