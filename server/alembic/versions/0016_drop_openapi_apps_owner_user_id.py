"""drop openapi_apps.owner_user_id (deprecated)

Revision ID: 0016_drop_openapi_apps_owner_user_id
Revises: 0015_add_developers_and_app_owner
Create Date: 2026-10-05 00:00:00.000000

移除 openapi_apps.owner_user_id 废弃字段：
- 归属已由 owner_type/owner_id 完全取代（developer → developers.id / admin → users.id）；
- owner_user_id 为无语义约束的历史裸 ID，无法区分两类用户，存量回填已于 0015 完成；
- 本迁移删除 idx_owner_user_id 索引与 owner_user_id 列，字段自 0015 起不再有代码写入。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0016_drop_openapi_apps_owner_user_id"
down_revision = "0015_add_developers_and_app_owner"
branch_labels = None
depends_on = None


def _table_has_column(table: str, column: str) -> bool:
    """检测目标表是否已存在指定列（幂等迁移用）。"""
    bind = op.get_bind()
    columns = [c["name"] for c in sa.inspect(bind).get_columns(table)]
    return column in columns


def _index_exists(table: str, index_name: str) -> bool:
    """检测目标表是否已存在指定索引（MySQL 不支持 DROP INDEX IF EXISTS）。"""
    bind = op.get_bind()
    names = [i["name"] for i in sa.inspect(bind).get_indexes(table)]
    return index_name in names


def upgrade() -> None:
    # 1. 先删索引再删列（MySQL 依赖列上的索引必须先释放）
    if _index_exists("openapi_apps", "idx_owner_user_id"):
        op.drop_index("idx_owner_user_id", table_name="openapi_apps")
    # 2. 删列（幂等：列不存在则跳过）
    if _table_has_column("openapi_apps", "owner_user_id"):
        op.drop_column("openapi_apps", "owner_user_id")


def downgrade() -> None:
    # 回滚：重建历史字段（仅结构，不负责回填数据）
    if not _table_has_column("openapi_apps", "owner_user_id"):
        op.add_column(
            "openapi_apps",
            sa.Column("owner_user_id", sa.BigInteger(), nullable=True, comment="[已废弃] 历史归属用户ID，仅存量数据"),
        )
    if not _index_exists("openapi_apps", "idx_owner_user_id"):
        op.create_index("idx_owner_user_id", "openapi_apps", ["owner_user_id"])
