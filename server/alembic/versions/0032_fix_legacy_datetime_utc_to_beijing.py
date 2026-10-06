"""fix legacy datetime columns from UTC to Beijing time (UTC+8)

Revision ID: 0032_fix_legacy_datetime_utc_to_beijing
Revises: 0031_add_openapi_apps_app_key_viewed_at
Create Date: 2026-10-06 22:00:00.000000

背景：MySQL 系统时区为 UTC（system_time_zone='UTC'），历史数据中由
CURRENT_TIMESTAMP 默认值或 datetime.now(UTC) 写入的时间列落库为 UTC，
比北京时间早 8 小时。本迁移将确认是 UTC 来源的存量时间列统一 +8 小时。

不动（本就是本地时间写入）的列：
- audit_logs.created_at          （audit_service 显式 datetime.now()）
- announcements.updated_at       （announcement_service 显式 datetime.now()）
- openapi_apps.last_used_at      （repository 显式 datetime.now()）
- station_messages.read_at       （repository 显式 datetime.now()）
- users.birthday / 各 deleted_at / receive_at / sent_at（无数据或日期类型）
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

# (表, 列) 列表：确认存的是 UTC，需要 +8 小时转为北京时间
UTC_COLUMNS: list[tuple[str, str]] = [
    ("announcements", "created_at"),
    ("assistant_conversations", "created_at"),
    ("assistant_conversations", "updated_at"),
    ("assistant_feedbacks", "created_at"),
    ("assistant_messages", "created_at"),
    ("developer_messages", "created_at"),
    ("developer_messages", "updated_at"),
    ("developers", "created_at"),
    ("developers", "updated_at"),
    ("developers", "last_login_at"),
    ("files", "created_at"),
    ("files", "updated_at"),
    ("login_logs", "created_at"),
    ("menus", "created_at"),
    ("menus", "updated_at"),
    ("notification_records", "created_at"),
    ("notifications_delivery", "created_at"),
    ("notifications_delivery", "updated_at"),
    ("openapi_app_registrations", "created_at"),
    ("openapi_app_registrations", "updated_at"),
    ("openapi_app_registrations", "approved_at"),
    ("openapi_apps", "created_at"),
    ("openapi_apps", "updated_at"),
    ("openapi_apps", "app_key_viewed_at"),
    ("roles", "created_at"),
    ("roles", "updated_at"),
    ("station_messages", "created_at"),
    ("system_notification_configs", "created_at"),
    ("system_notification_configs", "updated_at"),
    ("system_notifications", "created_at"),
    ("system_notifications", "updated_at"),
    ("user", "created_at"),
    ("user", "updated_at"),
    ("user_notification_configs", "created_at"),
    ("user_notification_configs", "updated_at"),
    ("users", "created_at"),
    ("users", "updated_at"),
    ("users", "last_login_at"),
]


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade() -> None:
    for table, column in UTC_COLUMNS:
        if not _column_exists(table, column):
            continue
        # 仅修正非 NULL 值，避免无谓扫描
        op.execute(
            f"UPDATE {table} SET {column} = DATE_ADD({column}, INTERVAL 8 HOUR) "
            f"WHERE {column} IS NOT NULL"
        )


def downgrade() -> None:
    """回滚：将修正后的时间减回 8 小时（幂等前提：仅对存在的数据操作）。"""
    for table, column in UTC_COLUMNS:
        if not _column_exists(table, column):
            continue
        op.execute(
            f"UPDATE {table} SET {column} = DATE_SUB({column}, INTERVAL 8 HOUR) "
            f"WHERE {column} IS NOT NULL"
        )
