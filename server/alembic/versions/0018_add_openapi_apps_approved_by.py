"""add openapi_apps.approved_by

Revision ID: 0018_add_openapi_apps_approved_by
Revises: 0017_add_files_uploaded_by_app
Create Date: 2026-10-05 10:00:00.000000

开放应用审批人留痕：
- 新增 openapi_apps.approved_by 记录审批人（管理系统 users.id），
  未审批为 NULL，用于管理端"我审批的"类目过滤。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0018_add_openapi_apps_approved_by"
down_revision = "0017_add_files_uploaded_by_app"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """检测目标表是否已存在指定列（幂等迁移用）。"""
    bind = op.get_bind()
    return column in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade() -> None:
    if not _column_exists("openapi_apps", "approved_by"):
        op.add_column(
            "openapi_apps",
            sa.Column("approved_by", sa.BigInteger(), nullable=True, comment="审批人用户ID（管理系统 users.id），未审批为 NULL"),
        )


def downgrade() -> None:
    if _column_exists("openapi_apps", "approved_by"):
        op.drop_column("openapi_apps", "approved_by")
