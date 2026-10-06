"""rename system_notice_delivery -> notifications_delivery

Revision ID: 0029
Revises: 0028_merge_notification_preferences
Create Date: 2026-10-06

变更：
1. 表名 system_notice_delivery -> notifications_delivery（去掉 system 前缀，来源多样）；
2. source 列移到 system_notification_id 之前（列顺序调整，MySQL 用 AFTER 子句）；
3. recipient 列宽 256 -> 512；
4. 清理历史冗余的 channel='station' 行（站内信由独立 station_messages 表承载，不写本表）；
5. 新增 idx_delivery_source 索引。
"""

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028_merge_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 清理 station 渠道冗余投递记录
    op.execute("DELETE FROM system_notice_delivery WHERE channel = 'station'")

    # 2) recipient 列宽 256 -> 512
    op.alter_column(
        "system_notice_delivery",
        "recipient",
        existing_type=sa.String(length=256),
        type_=sa.String(length=512),
        existing_nullable=False,
    )

    # 3) 表重命名
    op.rename_table("system_notice_delivery", "notifications_delivery")

    # 4) 列顺序：source 移到 system_notification_id 之前
    #    MySQL 通过 MODIFY COLUMN ... FIRST 调整列位置；类型与默认值保持不变。
    op.execute(
        "ALTER TABLE notifications_delivery "
        "MODIFY COLUMN source VARCHAR(32) NOT NULL "
        "COMMENT '通知来源（system_notice/alert/openapi_app/manual）' FIRST"
    )

    # 5) 新增 source 索引
    op.create_index("idx_delivery_source", "notifications_delivery", ["source"])


def downgrade() -> None:
    op.drop_index("idx_delivery_source", table_name="notifications_delivery")
    op.rename_table("notifications_delivery", "system_notice_delivery")
    op.alter_column(
        "system_notice_delivery",
        "recipient",
        existing_type=sa.String(length=512),
        type_=sa.String(length=256),
        existing_nullable=False,
    )
