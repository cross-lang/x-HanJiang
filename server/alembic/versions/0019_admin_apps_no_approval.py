"""openapi_apps.approval_status nullable + admin-owned backfill

Revision ID: 0019_admin_apps_no_approval
Revises: 0018_add_openapi_apps_approved_by
Create Date: 2026-10-05 12:00:00.000000

管理端自建应用无审批概念：
- approval_status 改为可空（开发者自助应用仍用 pending/approved/rejected）；
- 历史 admin 归属且已通过的应用回填 NULL（自建应用不应有审批状态）。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0019_admin_apps_no_approval"
down_revision = "0018_add_openapi_apps_approved_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 列改为可空
    op.alter_column(
        "openapi_apps",
        "approval_status",
        existing_type=sa.String(20),
        nullable=True,
        existing_server_default=sa.text("'pending'"),
    )
    # 2) 历史管理端自建应用回填 NULL（owner_type='admin'，旧逻辑曾写 approved）
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE openapi_apps SET approval_status = NULL "
            "WHERE owner_type = 'admin' AND approval_status IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.alter_column(
        "openapi_apps",
        "approval_status",
        existing_type=sa.String(20),
        nullable=False,
        existing_server_default=sa.text("'pending'"),
    )
