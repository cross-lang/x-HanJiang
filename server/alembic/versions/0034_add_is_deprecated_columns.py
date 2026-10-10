"""add is_deprecated columns to permissions / openapi_scopes

Revision ID: 0034_add_is_deprecated_columns
Revises: 0033_create_assistant_user_profiles
Create Date: 2026-10-10 13:30:00.000000

历史迁移链遗漏的列演进（旧数据库卷通过 create_all 建表后不会自动补列，
导致启动时 ORM 查询报 1054 Unknown column）。本迁移以"列存在性检查"
实现幂等补列/删列：
    - permissions.is_deprecated
    - openapi_scopes.is_deprecated
    - users.gender / users.birthday（模型新增）
    - users.age（模型已移除的遗留列，存在则删除）
    - users.role_id（模型已移除的遗留单角色列，含 idx_role_id 索引，存在则删除）
对已具备目标状态的环境（全新 create_all 建表）执行 upgrade 会安全跳过。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查目标表中是否已存在指定列（幂等判断）。"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [column["name"] for column in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """按列存在性补加缺失列，保证幂等可重复执行。"""
    if not _column_exists("permissions", "is_deprecated"):
        op.add_column(
            "permissions",
            sa.Column(
                "is_deprecated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
                comment="是否已废弃（路由中不再使用）",
            ),
        )
    if not _column_exists("openapi_scopes", "is_deprecated"):
        op.add_column(
            "openapi_scopes",
            sa.Column(
                "is_deprecated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
                comment="是否已废弃（路由中不再使用）",
            ),
        )
    if not _column_exists("users", "gender"):
        op.add_column(
            "users",
            sa.Column(
                "gender",
                sa.String(length=10),
                nullable=False,
                server_default="male",
                comment="性别：male/female",
            ),
        )
    if not _column_exists("users", "birthday"):
        op.add_column(
            "users",
            sa.Column(
                "birthday",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("'2000-01-01 00:00:00'"),
                comment="生日",
            ),
        )
    if _column_exists("users", "age"):
        op.drop_column("users", "age")
    if _column_exists("users", "role_id"):
        op.drop_column("users", "role_id")


def downgrade() -> None:
    """回滚：删除新增列、恢复遗留列（同样按存在性判断）。"""
    if _column_exists("permissions", "is_deprecated"):
        op.drop_column("permissions", "is_deprecated")
    if _column_exists("openapi_scopes", "is_deprecated"):
        op.drop_column("openapi_scopes", "is_deprecated")
    if _column_exists("users", "gender"):
        op.drop_column("users", "gender")
    if _column_exists("users", "birthday"):
        op.drop_column("users", "birthday")
    if not _column_exists("users", "age"):
        op.add_column(
            "users",
            sa.Column("age", sa.Integer(), nullable=True, comment="年龄（历史遗留字段）"),
        )
    if not _column_exists("users", "role_id"):
        op.add_column(
            "users",
            sa.Column("role_id", sa.BigInteger(), nullable=True, comment="主角色ID（历史遗留单角色列）"),
        )
