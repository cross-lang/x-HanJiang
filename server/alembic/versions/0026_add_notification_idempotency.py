"""add client_request_id to system_notifications

Revision ID: 0026
Revises: 0025_refactor_notification_delivery
Create Date: 2026-10-06

为 system_notifications 增加发布幂等键 client_request_id（唯一索引），
支撑 POST /notifications/publish 的幂等语义：同一请求键重复提交返回首次结果。
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025_refactor_notification_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_notifications",
        sa.Column("client_request_id", sa.String(length=64), nullable=True, comment="发布幂等键"),
    )
    op.create_index(
        "uq_notice_client_request",
        "system_notifications",
        ["client_request_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_notice_client_request", table_name="system_notifications")
    op.drop_column("system_notifications", "client_request_id")
