"""add openapi_apps.app_key_viewed_at

Revision ID: 0031_add_openapi_apps_app_key_viewed_at
Revises: 0030_move_event_type_after_user_id
Create Date: 2026-10-06 12:00:00.000000

"查看密钥"一次性语义：
- 新增 openapi_apps.app_key_viewed_at 记录明文 AppKey 最近一次查看时间，
  NULL=尚未查看过（创建审批通过后可查看一次），非 NULL=已展示过，
  此后只能通过重置密钥再次获取新明文（重置时该字段清空）。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """检测目标表是否已存在指定列（幂等迁移用）。"""
    bind = op.get_bind()
    return column in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade() -> None:
    if not _column_exists("openapi_apps", "app_key_viewed_at"):
        op.add_column(
            "openapi_apps",
            sa.Column(
                "app_key_viewed_at",
                sa.DateTime(),
                nullable=True,
                comment="AppKey 明文最近一次查看时间（NULL=未查看过）",
            ),
        )


def downgrade() -> None:
    if _column_exists("openapi_apps", "app_key_viewed_at"):
        op.drop_column("openapi_apps", "app_key_viewed_at")
