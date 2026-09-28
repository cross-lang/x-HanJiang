"""add is_pinned to assistant_conversations

Revision ID: 0009_add_pinned_to_assistant_conversations
Revises: 0008_create_assistant
Create Date: 2026-09-28 23:30:00.000000

AI 助手会话置顶字段：置顶会话在列表中优先展示（is_pinned DESC, updated_at DESC）。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_add_pinned_to_assistant_conversations"
down_revision = "0008_create_assistant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_conversations",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="是否置顶",
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "is_pinned")
