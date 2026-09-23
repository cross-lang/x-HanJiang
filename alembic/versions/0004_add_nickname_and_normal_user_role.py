"""add permissions

Revision ID: 0004_add_permissions
Revises: 0003_create_user_notification_configs
Create Date: 2026-09-23 21:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_add_permissions"
down_revision = "0003_create_user_notification_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 补充内置权限（如果不存在）
    permissions = [
        ("user:view", "查看用户", "user", "view", "查看用户列表与详情", 1),
        ("user:create", "创建用户", "user", "create", "创建新用户", 2),
        ("user:edit", "编辑用户", "user", "edit", "编辑用户信息", 3),
        ("user:delete", "删除用户", "user", "delete", "删除用户", 4),
        ("user:export", "导出用户", "user", "export", "导出用户列表", 5),
        ("user:import", "导入用户", "user", "import", "导入用户列表", 6),
        ("role:view", "查看角色", "role", "view", "查看角色列表与详情", 10),
        ("role:create", "创建角色", "role", "create", "创建新角色", 11),
        ("role:edit", "编辑角色", "role", "edit", "编辑角色信息", 12),
        ("role:delete", "删除角色", "role", "delete", "删除角色", 13),
        ("file:view", "查看文件", "file", "view", "查看文件列表与详情", 20),
        ("file:create", "上传文件", "file", "create", "上传文件", 21),
        ("file:delete", "删除文件", "file", "delete", "删除文件", 22),
        ("audit:view", "查看审计日志", "audit", "view", "查看业务审计日志", 30),
        ("notification:view", "查看通知", "notification", "view", "查看通知记录", 40),
        ("notification:create", "创建通知", "notification", "create", "创建通知配置", 41),
    ]
    for code, name, module, op_type, desc, sort in permissions:
        op.execute(
            f"""
            INSERT INTO permissions (perm_code, perm_name, module, operation, description, sort_order)
            SELECT '{code}', '{name}', '{module}', '{op_type}', '{desc}', {sort}
            FROM DUAL
            WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE perm_code = '{code}')
            """
        )

    # 超级管理员角色绑定全部权限
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.role_code = 'super_admin'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )


def downgrade() -> None:
    pass