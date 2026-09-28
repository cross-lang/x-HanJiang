"""create announcements

Revision ID: 0007_create_announcements
Revises: 0006_create_system_notifications
Create Date: 2026-09-28 11:00:00.000000

公告表：首页板块/横幅展示的公告，支持创建/修改/删除/发布/下架，
带有效期（start_at ~ end_at），正文支持 Markdown 与富文本两种格式。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_create_announcements"
down_revision = "0006_create_system_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("title", sa.String(200), nullable=False, comment="公告标题"),
        sa.Column("content", sa.Text(), nullable=False, comment="公告正文"),
        sa.Column(
            "content_type",
            sa.String(16),
            nullable=False,
            server_default="markdown",
            comment="正文格式（markdown/richtext）",
        ),
        sa.Column(
            "position", sa.String(16), nullable=False, server_default="board", comment="展示位置（board/banner）"
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="draft",
            comment="发布状态（draft/published/unpublished）",
        ),
        sa.Column("start_at", sa.DateTime(), nullable=True, comment="生效开始时间"),
        sa.Column("end_at", sa.DateTime(), nullable=True, comment="生效结束时间"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="展示排序（越小越靠前）"),
        sa.Column("operator_id", sa.BigInteger(), nullable=True, comment="操作人用户ID"),
        sa.Column("operator_name", sa.String(100), nullable=True, comment="操作人用户名"),
        sa.Column("published_at", sa.DateTime(), nullable=True, comment="发布时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
    )
    op.create_index("idx_announcement_status", "announcements", ["status"])
    op.create_index("idx_announcement_position", "announcements", ["position"])
    op.create_index("idx_announcement_period", "announcements", ["start_at", "end_at"])


def downgrade() -> None:
    op.drop_index("idx_announcement_period", table_name="announcements")
    op.drop_index("idx_announcement_position", table_name="announcements")
    op.drop_index("idx_announcement_status", table_name="announcements")
    op.drop_table("announcements")
