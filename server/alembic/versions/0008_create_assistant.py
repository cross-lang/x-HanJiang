"""create assistant tables

Revision ID: 0008_create_assistant
Revises: 0007_create_announcements
Create Date: 2026-09-28 22:00:00.000000

AI 助手三张表：
    - assistant_conversations: 会话（含第 2 层记忆的滚动摘要字段 summary）
    - assistant_messages:      会话消息（仅持久化 user / assistant 角色）
    - assistant_feedbacks:     用户对消息质量的 👍👎 反馈（提示词调优数据源）
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_create_assistant"
down_revision = "0007_create_announcements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="所属用户ID"),
        sa.Column("summary", sa.Text(), nullable=True, comment="滚动摘要（第2层记忆，压缩远历史）"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_assistant_conv_user", "assistant_conversations", ["user_id"])

    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
            comment="所属会话ID",
        ),
        sa.Column("role", sa.String(20), nullable=False, comment="消息角色：user/assistant"),
        sa.Column("content", sa.Text(), nullable=False, comment="消息内容"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_assistant_msg_conv", "assistant_messages", ["conversation_id"])

    op.create_table(
        "assistant_feedbacks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
            comment="会话ID",
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False, comment="被反馈的消息ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="反馈用户ID"),
        sa.Column("positive", sa.Boolean(), nullable=False, comment="是否好评：true 好评 / false 差评"),
        sa.Column("comment", sa.String(500), nullable=True, comment="补充意见"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_assistant_feedback_conv", "assistant_feedbacks", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("idx_assistant_feedback_conv", table_name="assistant_feedbacks")
    op.drop_table("assistant_feedbacks")
    op.drop_index("idx_assistant_msg_conv", table_name="assistant_messages")
    op.drop_table("assistant_messages")
    op.drop_index("idx_assistant_conv_user", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
