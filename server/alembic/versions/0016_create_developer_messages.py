"""create developer_messages

Revision ID: 0016_create_developer_messages
Revises: 0015_add_developers_and_app_owner
Create Date: 2026-10-03 15:30:00.000000

开放平台开发者站内信表：
1. developer_messages：开发者门户站内信（与管理系统用户站内信 notification_records 分表），
   developer_id 直接绑定开发者（developers.id），字段按 web/open 前端
   OpenMessage 约定（title/content/category/read/created_at）设计；
2. 索引：idx_dev_msg_developer（developer_id），支撑"我的站内信"按收件人过滤。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0016_create_developer_messages"
down_revision = "0015_add_developers_and_app_owner"
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    """检测目标表是否已存在（幂等迁移用）。"""
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table)


def _index_exists(table: str, index_name: str) -> bool:
    """检测目标表是否已存在指定索引（MySQL 不支持 CREATE INDEX IF NOT EXISTS）。"""
    bind = op.get_bind()
    names = [i["name"] for i in sa.inspect(bind).get_indexes(table)]
    return index_name in names


def upgrade() -> None:
    # 表可能已由早期 metadata.create_all 创建（空表），此处幂等处理：
    # 已存在则仅补齐索引，不存在则建表。
    if not _table_exists("developer_messages"):
        op.create_table(
            "developer_messages",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
            sa.Column("developer_id", sa.BigInteger(), nullable=False, comment="收件开发者ID（developers.id）"),
            sa.Column("title", sa.String(200), nullable=False, comment="消息标题"),
            sa.Column("content", sa.Text(), nullable=False, comment="消息正文"),
            sa.Column(
                "category",
                sa.String(20),
                nullable=False,
                server_default="system",
                comment="消息类型：system/audit/notify",
            ),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="unread",
                comment="阅读状态：unread/read",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
    if not _index_exists("developer_messages", "idx_dev_msg_developer"):
        op.create_index("idx_dev_msg_developer", "developer_messages", ["developer_id"])


def downgrade() -> None:
    op.drop_index("idx_dev_msg_developer", table_name="developer_messages")
    op.drop_table("developer_messages")
