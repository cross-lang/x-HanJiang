"""create assistant_user_profiles table

Revision ID: 0033_create_assistant_user_profiles
Revises: 0032_fix_legacy_datetime_utc_to_beijing
Create Date: 2026-10-09 22:00:00.000000

AI 助手用户长期档案表（第 1 层记忆持久化）：
    - assistant_user_profiles: 一个用户一条档案，由 LLM 从历史对话中
      定期抽取更新，跨会话沉淀，注入系统提示词实现个性化服务。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_user_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="所属用户ID"),
        sa.Column("profile", sa.Text(), nullable=True, comment="用户档案文本（LLM 抽取沉淀）"),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="版本号（乐观锁，防并发抽取覆盖）",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_assistant_profile_user", "assistant_user_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_assistant_profile_user", table_name="assistant_user_profiles")
    op.drop_table("assistant_user_profiles")
