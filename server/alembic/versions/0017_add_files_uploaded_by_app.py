"""add files.uploaded_by_app

Revision ID: 0017_add_files_uploaded_by_app
Revises: 0016_create_developer_messages
Create Date: 2026-10-03 16:00:00.000000

开放接口（AppId/Key 签名域）文件上传以应用为操作主体：
- files.uploaded_by 保持"用户归属"语义（管理系统上传人 users.id，int 外键）；
- 新增 files.uploaded_by_app 记录开放接口上传方应用 ID（openapi_apps.app_id），
  两列互斥可空，避免把应用 ID 误写入用户外键列。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0017_add_files_uploaded_by_app"
down_revision = "0016_create_developer_messages"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """检测目标表是否已存在指定列（幂等迁移用）。"""
    bind = op.get_bind()
    return column in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade() -> None:
    if not _column_exists("files", "uploaded_by_app"):
        op.add_column(
            "files",
            sa.Column("uploaded_by_app", sa.String(64), nullable=True, comment="上传应用ID（开放接口上传方 openapi_apps.app_id）"),
        )


def downgrade() -> None:
    if _column_exists("files", "uploaded_by_app"):
        op.drop_column("files", "uploaded_by_app")
