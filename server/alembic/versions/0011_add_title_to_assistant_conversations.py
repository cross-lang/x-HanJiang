"""add title to assistant_conversations

Revision ID: 0011_add_title_to_assistant_conversations
Revises: 0010_add_deleted_at_to_assistant_conversations
Create Date: 2026-09-29 00:40:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0011_add_title_to_assistant_conversations"
down_revision = "0010_add_deleted_at_to_assistant_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 会话主题名（AI 自动归纳，页面展示；暂不支持用户手动修改）
    op.add_column(
        "assistant_conversations",
        sa.Column("title", sa.String(length=60), nullable=True, comment="会话主题名（AI 自动归纳）"),
    )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "title")
