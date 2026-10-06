"""move event_type column right after user_id

Revision ID: 0030
Revises: 0029_rename_notifications_delivery
Create Date: 2026-10-06

将 user_notification_configs.event_type 列移动到 user_id 之后，
使表结构顺序与 ORM 定义一致：id → user_id → event_type → channel → ...
"""

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL: MODIFY COLUMN ... AFTER user_id 调整列物理顺序
    op.execute(
        "ALTER TABLE user_notification_configs "
        "MODIFY COLUMN event_type VARCHAR(64) NOT NULL COMMENT '事件类型（如 user.password_changed）' "
        "AFTER user_id"
    )


def downgrade() -> None:
    # 回退：event_type 移到表末尾（无 AFTER 指定时 MySQL 不保证位置，此处仅做最小回退）
    op.execute(
        "ALTER TABLE user_notification_configs "
        "MODIFY COLUMN event_type VARCHAR(64) NOT NULL COMMENT '事件类型（如 user.password_changed）'"
    )
