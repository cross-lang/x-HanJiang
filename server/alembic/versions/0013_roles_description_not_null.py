"""roles description not null

Revision ID: 0013_roles_description_not_null
Revises: 0012_users_required_fields
Create Date: 2026-10-02 11:30:00.000000

创建角色必填治理（与 RoleCreateRequest / RoleEntity 收紧保持一致）：
- roles.description 置为 NOT NULL（存量 4 个系统角色均有描述，无需回填）
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0013_roles_description_not_null"
down_revision = "0012_users_required_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 防御性回填：如有历史空描述，兜底为角色名称（正常迁移路径下应无空值）
    op.execute("UPDATE roles SET description = role_name WHERE description IS NULL OR description = ''")
    op.alter_column("roles", "description", existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    op.alter_column("roles", "description", existing_type=sa.String(length=255), nullable=True)
