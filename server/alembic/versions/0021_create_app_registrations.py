"""openapi_apps 去审批字段 + 新增应用申请表

Revision ID: 0021_create_app_registrations
Revises: 0020_drop_approval_status_default
Create Date: 2026-10-06 10:00:00.000000

业务变更：应用申请/审批从 openapi_apps 解耦为按批次记录的申请表：
- 新建表 openapi_app_registrations（每次创建/修改申请为一条记录，含内容快照与审批结果）；
- openapi_apps 新增 approved 列（应用级授权状态，网关放行门槛）；
- 存量审批字段（approval_status / approved_by / approval_note / scope_apply_reason）迁移至申请表后删除。

存量数据迁移规则：
- 开发者应用（approval_status 非 NULL）：按当前应用内容生成一条 create 申请记录，
  审批状态 / 审批人 / 审批意见 / 申请说明原样迁移；approved 按审批结果回填（approved→1，其余→0）；
- 管理端自建应用（approval_status 为 NULL）：无审批概念，approved 直接置 1。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0021_create_app_registrations"
down_revision = "0020_drop_approval_status_default"
branch_labels = None
depends_on = None

_APPROVAL_COLUMNS = ["approval_status", "approved_by", "approval_note", "scope_apply_reason"]


def upgrade() -> None:
    bind = op.get_bind()

    # 1. 新建应用申请表
    op.create_table(
        "openapi_app_registrations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("app_id", sa.BigInteger(), nullable=False, comment="应用ID（openapi_apps.id）"),
        sa.Column(
            "registration_type",
            sa.String(length=20),
            nullable=False,
            comment="申请类型：create 创建申请 / update 修改申请",
        ),
        sa.Column("name", sa.String(length=100), nullable=False, comment="申请的应用名"),
        sa.Column("description", sa.String(length=255), nullable=False, comment="申请的应用描述"),
        sa.Column(
            "scopes",
            sa.String(length=500),
            server_default="",
            nullable=False,
            comment="申请的权限范围，逗号分隔",
        ),
        sa.Column(
            "auth_mode",
            sa.String(length=10),
            server_default="plain",
            nullable=False,
            comment="申请的鉴权模式：plain/hmac/both",
        ),
        sa.Column("apply_reason", sa.String(length=255), nullable=True, comment="开发者填写的申请说明/用途"),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
            comment="审批状态：pending/approved/rejected",
        ),
        sa.Column("approved_by", sa.BigInteger(), nullable=True, comment="审批人用户ID，未审批为 NULL"),
        sa.Column("approval_note", sa.String(length=255), nullable=True, comment="审批意见/驳回原因"),
        sa.Column("approved_at", sa.DateTime(), nullable=True, comment="审批时间"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_reg_app", "openapi_app_registrations", ["app_id"])
    op.create_index("idx_reg_status", "openapi_app_registrations", ["status"])

    # 2. openapi_apps 新增 approved 列（先按无审批概念的存量应用兜底置 1，随后按审批结果精确回填）
    op.add_column(
        "openapi_apps",
        sa.Column("approved", sa.Boolean(), server_default=sa.text("1"), nullable=False, comment="是否已通过创建审批"),
    )

    # 3. 存量审批字段迁移至申请表
    rows = bind.execute(
        sa.text(
            "SELECT id, app_id, name, description, scopes, auth_mode, owner_type, "
            "approval_status, approved_by, approval_note, scope_apply_reason "
            "FROM openapi_apps WHERE approval_status IS NOT NULL"
        )
    ).mappings().all()
    for r in rows:
        bind.execute(
            sa.text(
                "INSERT INTO openapi_app_registrations "
                "(app_id, registration_type, name, description, scopes, auth_mode, apply_reason, "
                "status, approved_by, approval_note, created_at, updated_at) "
                "VALUES (:app_id, 'create', :name, :description, :scopes, :auth_mode, :apply_reason, "
                ":status, :approved_by, :approval_note, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "app_id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "scopes": r["scopes"] or "",
                "auth_mode": r["auth_mode"] or "plain",
                "apply_reason": r["scope_apply_reason"],
                "status": r["approval_status"],
                "approved_by": r["approved_by"],
                "approval_note": r["approval_note"],
            },
        )
    # 按审批结果回填 approved（仅开发者应用存在审批字段；通过→1，其余→0）
    bind.execute(
        sa.text("UPDATE openapi_apps SET approved = 1 WHERE approval_status = 'approved'")
    )
    bind.execute(
        sa.text(
            "UPDATE openapi_apps SET approved = 0 "
            "WHERE approval_status IS NOT NULL AND approval_status <> 'approved'"
        )
    )

    # 4. 删除应用表上的审批字段
    for col in _APPROVAL_COLUMNS:
        op.drop_column("openapi_apps", col)


def downgrade() -> None:
    bind = op.get_bind()

    # 1. 恢复应用表审批字段（nullable）
    op.add_column("openapi_apps", sa.Column("approval_status", sa.String(length=20), nullable=True))
    op.add_column("openapi_apps", sa.Column("approved_by", sa.BigInteger(), nullable=True))
    op.add_column("openapi_apps", sa.Column("approval_note", sa.String(length=255), nullable=True))
    op.add_column("openapi_apps", sa.Column("scope_apply_reason", sa.String(length=255), nullable=True))

    # 2. 从申请表回填（每应用取最新一条注册记录近似还原；开发者为 create 类型）
    rows = bind.execute(
        sa.text(
            "SELECT r.app_id, r.status, r.approved_by, r.approval_note, r.apply_reason "
            "FROM openapi_app_registrations r "
            "INNER JOIN (SELECT app_id, MAX(id) AS max_id FROM openapi_app_registrations GROUP BY app_id) m "
            "ON r.id = m.max_id"
        )
    ).mappings().all()
    for r in rows:
        bind.execute(
            sa.text(
                "UPDATE openapi_apps SET approval_status = :status, approved_by = :approved_by, "
                "approval_note = :approval_note, scope_apply_reason = :apply_reason WHERE id = :app_id"
            ),
            {
                "status": r["status"],
                "approved_by": r["approved_by"],
                "approval_note": r["approval_note"],
                "apply_reason": r["apply_reason"],
                "app_id": r["app_id"],
            },
        )
    # 无申请记录（管理员自建）的应用：approval_status 置 NULL
    bind.execute(
        sa.text(
            "UPDATE openapi_apps SET approval_status = NULL "
            "WHERE NOT EXISTS (SELECT 1 FROM openapi_app_registrations r WHERE r.app_id = openapi_apps.id)"
        )
    )

    # 3. 删除 approved 列与申请表
    op.drop_column("openapi_apps", "approved")
    op.drop_index("idx_reg_status", table_name="openapi_app_registrations")
    op.drop_index("idx_reg_app", table_name="openapi_app_registrations")
    op.drop_table("openapi_app_registrations")
