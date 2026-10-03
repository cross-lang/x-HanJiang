"""add developers and openapi_apps owner/approval fields

Revision ID: 0015_add_developers_and_app_owner
Revises: 0014_openapi_apps_description_not_null
Create Date: 2026-10-03 14:00:00.000000

开放平台开发者域落地：
1. developers 表：开放平台门户账号（与管理系统 users 分表）；
2. openapi_apps 增加归属与审批字段：
   - owner_type：developer（开发者自助）/ admin（管理员分配）
   - owner_id：归属方 ID（developer → developers.id / admin → users.id）
   - approval_status / approval_note / scope_apply_reason：scope 申请审批流
3. 存量回填：历史应用全部为管理员创建 → owner_type='admin'、owner_id=owner_user_id、
   approval_status='approved'（管理员已直接配好 scope）；
4. 索引：新增 idx_owner(owner_type, owner_id)，保留 idx_owner_user_id（历史列仍存）。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0015_add_developers_and_app_owner"
down_revision = "0014_openapi_apps_description_not_null"
branch_labels = None
depends_on = None


def _table_has_column(table: str, column: str) -> bool:
    """检测目标表是否已存在指定列（幂等迁移用）。"""
    bind = op.get_bind()
    columns = [c["name"] for c in sa.inspect(bind).get_columns(table)]
    return column in columns


def _table_exists(table: str) -> bool:
    """检测目标表是否已存在。"""
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table)


def _index_exists(table: str, index_name: str) -> bool:
    """检测目标表是否已存在指定索引（MySQL 不支持 CREATE INDEX IF NOT EXISTS）。"""
    bind = op.get_bind()
    names = [i["name"] for i in sa.inspect(bind).get_indexes(table)]
    return index_name in names


def upgrade() -> None:
    # 1. 开发者账号表（与管理系统 users 分表）
    #   表可能已由早期 metadata.create_all 创建（空表），此处幂等处理：
    #   已存在则仅补齐唯一索引，不存在则建表。
    if not _table_exists("developers"):
        op.create_table(
            "developers",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
            sa.Column("username", sa.String(50), nullable=False, comment="用户名（全局唯一）"),
            sa.Column("email", sa.String(100), nullable=False, comment="邮箱（全局唯一）"),
            sa.Column("password_hash", sa.String(255), nullable=False, comment="密码哈希（bcrypt）"),
            sa.Column("name", sa.String(100), nullable=False, server_default="", comment="姓名/昵称"),
            sa.Column("phone", sa.String(20), nullable=False, server_default="", comment="手机号"),
            sa.Column("certification_type", sa.String(20), nullable=True, comment="认证类型：personal/enterprise"),
            sa.Column(
                "certification_status",
                sa.String(20),
                nullable=False,
                server_default="none",
                comment="认证状态：none/pending/approved/rejected",
            ),
            sa.Column("company_name", sa.String(200), nullable=True, comment="企业名称（企业认证）"),
            sa.Column("credential_no", sa.String(100), nullable=True, comment="证件号"),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="enabled",
                comment="状态：enabled/disabled",
            ),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
    if not _index_exists("developers", "uk_developer_username"):
        op.create_index("uk_developer_username", "developers", ["username"], unique=True)
    if not _index_exists("developers", "uk_developer_email"):
        op.create_index("uk_developer_email", "developers", ["email"], unique=True)

    # 2. openapi_apps 归属与审批字段（幂等：列已存在则跳过）
    if not _table_has_column("openapi_apps", "owner_type"):
        op.add_column(
            "openapi_apps",
            sa.Column(
                "owner_type",
                sa.String(20),
                nullable=False,
                server_default="admin",
                comment="归属类型：developer 开发者自助 / admin 管理员分配",
            ),
        )
    if not _table_has_column("openapi_apps", "owner_id"):
        op.add_column(
            "openapi_apps",
            sa.Column(
                "owner_id",
                sa.BigInteger(),
                nullable=True,
                comment="归属方ID：developer→developers.id / admin→users.id",
            ),
        )
    if not _table_has_column("openapi_apps", "approval_status"):
        op.add_column(
            "openapi_apps",
            sa.Column(
                "approval_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
                comment="审批状态：pending/approved/rejected",
            ),
        )
    if not _table_has_column("openapi_apps", "approval_note"):
        op.add_column(
            "openapi_apps",
            sa.Column("approval_note", sa.String(255), nullable=True, comment="审批意见/驳回原因"),
        )
    if not _table_has_column("openapi_apps", "scope_apply_reason"):
        op.add_column(
            "openapi_apps",
            sa.Column("scope_apply_reason", sa.String(255), nullable=True, comment="开发者申请 scope 的申请说明"),
        )

    # 3. 存量回填：历史应用均为管理员创建（幂等，重复执行结果一致）
    op.execute(
        "UPDATE openapi_apps SET owner_type = 'admin', "
        "owner_id = owner_user_id, approval_status = 'approved' "
        "WHERE deleted_at IS NULL AND owner_type = 'admin' AND owner_id IS NULL"
    )

    # 4. 新索引：按 (owner_type, owner_id) 支撑"开发者只看自己"与管理端按来源筛选
    if not _index_exists("openapi_apps", "idx_owner"):
        op.create_index("idx_owner", "openapi_apps", ["owner_type", "owner_id"])


def downgrade() -> None:
    op.drop_index("idx_owner", table_name="openapi_apps")
    op.drop_column("openapi_apps", "scope_apply_reason")
    op.drop_column("openapi_apps", "approval_note")
    op.drop_column("openapi_apps", "approval_status")
    op.drop_column("openapi_apps", "owner_id")
    op.drop_column("openapi_apps", "owner_type")
    op.drop_index("uk_developer_email", table_name="developers")
    op.drop_index("uk_developer_username", table_name="developers")
    op.drop_table("developers")
