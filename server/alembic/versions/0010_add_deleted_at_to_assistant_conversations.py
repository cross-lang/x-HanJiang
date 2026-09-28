"""add deleted_at to assistant_conversations

Revision ID: 0010_add_deleted_at_to_assistant_conversations
Revises: 0009_add_pinned_to_assistant_conversations
Create Date: 2026-09-28 23:50:00.000000

会话软删除字段：删除时仅标记 deleted_at，消息与反馈物理保留留档。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0010_add_deleted_at_to_assistant_conversations"
down_revision = "0009_add_pinned_to_assistant_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_conversations",
        sa.Column(
            "deleted_at",
            sa.DateTime(),
            nullable=True,
            comment="软删除时间（NULL 表示未删除）",
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "deleted_at")
