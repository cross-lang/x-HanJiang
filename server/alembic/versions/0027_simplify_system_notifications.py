"""simplify system_notifications columns

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-06

精简 system_notifications 表结构：
1. maintenance_time / duration / reason 三列合并进 metadata_json（作为扩展字段）；
2. 删除 event_type 列（值固定为 system.notice，无独立存储必要）；
3. 删除 sent_at 列（与 published_at 语义重复，保留 published_at）；
4. 新增 updated_at 列（撤回/重新发布时刷新）。
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 新增 updated_at（与 created_at 同语义，撤回/重发时 onupdate 自动刷新）
    op.add_column(
        "system_notifications",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
            comment="最近更新时间",
        ),
    )

    # 2) 存量数据：把 maintenance_time / duration / reason 合并进 metadata_json
    #    MySQL: metadata_json 可能为 NULL，先用 IFNULL 兜底为空 JSON 对象再 merge
    op.execute(
        """
        UPDATE system_notifications
        SET metadata_json = JSON_MERGE_PATCH(
            IFNULL(metadata_json, JSON_OBJECT()),
            JSON_OBJECT(
                'maintenance_time', maintenance_time,
                'duration_hours', duration,
                'reason', reason
            )
        )
        WHERE maintenance_time IS NOT NULL
           OR duration IS NOT NULL
           OR reason IS NOT NULL
        """
    )

    # 3) 删除独立列
    op.drop_column("system_notifications", "maintenance_time")
    op.drop_column("system_notifications", "duration")
    op.drop_column("system_notifications", "reason")
    op.drop_column("system_notifications", "event_type")
    op.drop_column("system_notifications", "sent_at")


def downgrade() -> None:
    op.add_column(
        "system_notifications",
        sa.Column("sent_at", sa.DateTime(), nullable=True, comment="首次投递时间"),
    )
    op.add_column(
        "system_notifications",
        sa.Column(
            "event_type",
            sa.String(length=64),
            nullable=False,
            server_default="system.notice",
            comment="事件类型",
        ),
    )
    op.add_column(
        "system_notifications",
        sa.Column("reason", sa.String(length=500), nullable=True, comment="维护原因"),
    )
    op.add_column(
        "system_notifications",
        sa.Column("duration", sa.String(length=50), nullable=True, comment="预计持续时长"),
    )
    op.add_column(
        "system_notifications",
        sa.Column("maintenance_time", sa.String(length=50), nullable=True, comment="维护开始时间"),
    )
    op.drop_column("system_notifications", "updated_at")
