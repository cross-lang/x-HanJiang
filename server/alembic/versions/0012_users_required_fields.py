"""users required fields not null

Revision ID: 0012_users_required_fields
Revises: 0011_add_title_to_assistant_conversations
Create Date: 2026-10-02 10:00:00.000000

创建用户必填治理（与 UserCreateRequest / UserEntity 收紧保持一致）：
- name / password_hash / gender / birthday 置为 NOT NULL
- phone 置为 NOT NULL（存量空值回填 ''，含 NULL 与空串，保证唯一性约束场景下行为一致）
- birthday 存量 NULL 回填 '1970-01-01'（与 seed 中 superadmin 占位日期一致）
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0012_users_required_fields"
down_revision = "0011_add_title_to_assistant_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 存量数据回填（幂等：重复执行不会破坏已填充数据）
    op.execute("UPDATE users SET phone = '' WHERE phone IS NULL OR phone = ''")
    op.execute("UPDATE users SET birthday = '1970-01-01' WHERE birthday IS NULL")

    # 字段收紧为 NOT NULL
    op.alter_column("users", "name", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="",
    )
    op.alter_column("users", "gender", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("users", "birthday", existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    op.alter_column("users", "birthday", existing_type=sa.DateTime(), nullable=True)
    op.alter_column("users", "gender", existing_type=sa.String(length=10), nullable=True)
    op.alter_column("users", "phone", existing_type=sa.String(length=20), nullable=True, server_default=None)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("users", "name", existing_type=sa.String(length=100), nullable=True)
