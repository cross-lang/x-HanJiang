"""openapi_apps description not null

Revision ID: 0014_openapi_apps_description_not_null
Revises: 0013_roles_description_not_null
Create Date: 2026-10-02 12:00:00.000000

创建开放应用必填治理（与 OpenApiAppCreateRequest / OpenApiAppEntity 收紧保持一致）：
- openapi_apps.description 置为 NOT NULL
- 存量 NULL/空串描述回填为应用名（幂等）
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0014_openapi_apps_description_not_null"
down_revision = "0013_roles_description_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 存量回填：无描述时以应用名兜底
    op.execute("UPDATE openapi_apps SET description = name WHERE description IS NULL OR description = ''")
    op.alter_column("openapi_apps", "description", existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    op.alter_column("openapi_apps", "description", existing_type=sa.String(length=255), nullable=True)
