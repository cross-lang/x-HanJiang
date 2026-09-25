"""create openapi_apps

Revision ID: 0005_create_openapi_apps
Revises: 0004_add_permissions
Create Date: 2026-09-25 10:00:00.000000

开放平台应用表：面向服务/第三方应用的 AppId+AppKey 身份。
表结构已为未来升级 HMAC 签名鉴权预留 auth_mode 与 app_key_encrypted 列。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_create_openapi_apps"
down_revision = "0004_add_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "openapi_apps",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
        sa.Column("app_id", sa.String(64), nullable=False, comment="对外应用ID，带前缀如 hj_live_xxx"),
        sa.Column("app_key_hash", sa.String(128), nullable=False, comment="AppKey 的 SHA256 哈希"),
        sa.Column("app_key_encrypted", sa.Text(), nullable=True, comment="Fernet 加密的明文 AppKey，HMAC 模式解密用"),
        sa.Column("name", sa.String(100), nullable=False, comment="应用名"),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True, comment="归属人用户ID"),
        sa.Column("scopes", sa.String(500), nullable=False, server_default="", comment="逗号分隔的权限范围"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态"),
        sa.Column("auth_mode", sa.String(10), nullable=False, server_default="plain", comment="plain/hmac/both"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("uk_app_id", "openapi_apps", ["app_id"], unique=True)
    op.create_index("idx_owner_user_id", "openapi_apps", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("idx_owner_user_id", table_name="openapi_apps")
    op.drop_index("uk_app_id", table_name="openapi_apps")
    op.drop_table("openapi_apps")
