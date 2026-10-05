"""drop openapi_apps.approval_status server default

Revision ID: 0020_drop_approval_status_default
Revises: 0019_admin_apps_no_approval
Create Date: 2026-10-05 12:30:00.000000

移除 approval_status 的数据库默认 'pending'：
- SQLAlchemy 2.0 下带 server_default 的列在属性为 None 时会被 DB 默认兜底，
  导致管理端自建应用无法落 NULL；
- 开发者自助应用仍由代码显式写入 pending，不受影响。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0020_drop_approval_status_default"
down_revision = "0019_admin_apps_no_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "openapi_apps",
        "approval_status",
        existing_type=sa.String(20),
        nullable=True,
        existing_server_default=sa.text("'pending'"),
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "openapi_apps",
        "approval_status",
        existing_type=sa.String(20),
        nullable=True,
        server_default=sa.text("'pending'"),
    )
