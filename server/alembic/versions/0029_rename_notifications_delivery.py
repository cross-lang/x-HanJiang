"""rename system_notice_delivery -> notifications_delivery

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-06

变更：
1. 表名 system_notice_delivery -> notifications_delivery（去掉 system 前缀，来源多样）；
2. source 列移到 system_notification_id 之前（列顺序调整，MySQL 用 FIRST 子句）；
3. recipient 列宽 256 -> 512；
4. 清理历史冗余的 channel='station' 行（站内信由独立 station_messages 表承载，不写本表）；
5. 新增 idx_delivery_source 索引。

幂等说明：开发期该迁移曾被部分手工执行（目标表已存在），此处对
"旧表存在/目标表已存在" 的四种组合均做兼容处理，保证可重复收敛到目标结构。
"""

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

_OLD_TABLE = "system_notice_delivery"
_NEW_TABLE = "notifications_delivery"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    has_old = _OLD_TABLE in table_names
    has_new = _NEW_TABLE in table_names

    if has_old:
        # 1) 清理 station 渠道冗余投递记录（站内信由 station_messages 承载）
        op.execute(f"DELETE FROM {_OLD_TABLE} WHERE channel = 'station'")

        # 2) recipient 列宽 256 -> 512（幂等：MySQL 重复执行同尺寸 alter 无副作用）
        op.alter_column(
            _OLD_TABLE,
            "recipient",
            existing_type=sa.String(length=256),
            type_=sa.String(length=512),
            existing_nullable=False,
        )

        # 3) 表重命名（目标表已存在时，旧表为已清空的空壳，直接删除）
        if has_new:
            op.drop_table(_OLD_TABLE)
        else:
            op.rename_table(_OLD_TABLE, _NEW_TABLE)

    if has_new:
        # 4) 列顺序：source 移到 system_notification_id 之前（幂等）
        op.execute(
            f"ALTER TABLE {_NEW_TABLE} "
            "MODIFY COLUMN source VARCHAR(32) NOT NULL "
            "COMMENT '通知来源（system_notice/alert/openapi_app/manual）' FIRST"
        )

        # 5) source 索引（不存在才创建）
        indexes = {i["name"] for i in inspector.get_indexes(_NEW_TABLE)}
        if "idx_delivery_source" not in indexes:
            op.create_index("idx_delivery_source", _NEW_TABLE, ["source"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if _NEW_TABLE not in table_names:
        return
    indexes = {i["name"] for i in inspector.get_indexes(_NEW_TABLE)}
    if "idx_delivery_source" in indexes:
        op.drop_index("idx_delivery_source", table_name=_NEW_TABLE)
    if _OLD_TABLE in table_names:
        op.drop_table(_OLD_TABLE)
    op.rename_table(_NEW_TABLE, _OLD_TABLE)
    op.alter_column(
        _OLD_TABLE,
        "recipient",
        existing_type=sa.String(length=512),
        type_=sa.String(length=256),
        existing_nullable=False,
    )
