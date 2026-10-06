#!/usr/bin/env python3
"""通知体系重构：新增投递明细/站内信独立表，删除 notification_records。

Revision ID: 0025_refactor_notification_delivery
Revises: 0024_rename_system_notification_config_json
Create Date: 2026-10-06

变更内容：
- system_notifications 新增 event_type（默认 system.notice）、sent_at、metadata_json；
- 新建 system_notice_delivery（通知投递明细 + 失败重试队列，不携带 subject/content）；
- 新建 station_messages（管理系统用户站内信独立收件箱）；
- notification_records 存量数据迁移：站内信记录转 station_messages，
  全部记录转 system_notice_delivery（status 归一化，read→success）；
- 删除 notification_records 表。

说明：MySQL 非事务 DDL，中断后重跑可安全继续；对"旧表不存在"的库幂等跳过。
"""

import re
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0025_refactor_notification_delivery"
down_revision = "0024_rename_system_notification_config_json"
branch_labels = None
depends_on = None

_OLD_TABLE = "notification_records"

_USER_RECIPIENT_RE = re.compile(r"^user:(\d+)$")


def _has_table(bind: sa.engine.Connection, table: str) -> bool:
    """判断数据库中是否已存在指定表。"""
    return sa.inspect(bind).has_table(table)


def _normalize_status(status: str) -> str:
    """将旧 records 状态归一化为 delivery 状态（read→success 等）。"""
    return "success" if status == "read" else ("pending" if status == "retrying" else status)


def _map_source(event_type: str) -> str:
    """按事件类型映射通知来源。"""
    if event_type == "system.notice":
        return "system_notice"
    if event_type == "system.alert":
        return "alert"
    if event_type == "station.message":
        return "station"
    if event_type.startswith("openapi_app"):
        return "openapi_app"
    return "station"


def upgrade() -> None:
    bind = op.get_bind()

    # 0. system_notifications 表不存在时全量建表（兼容未建表的库），
    #    已存在则仅补列
    if not _has_table(bind, "system_notifications"):
        op.create_table(
            "system_notifications",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("title", sa.String(length=200), nullable=False, comment="通知标题"),
            sa.Column("content", sa.Text(), nullable=False, comment="通知正文"),
            sa.Column("notice_type", sa.String(length=32), nullable=False, server_default="notice", comment="通知类型（notice/maintenance）"),
            sa.Column("maintenance_time", sa.DateTime(), nullable=True, comment="维护开始时间"),
            sa.Column("duration", sa.String(length=64), nullable=True, comment="预计持续时长"),
            sa.Column("reason", sa.String(length=500), nullable=True, comment="维护原因"),
            sa.Column("event_type", sa.String(length=64), nullable=False, server_default="system.notice", comment="事件类型"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="published", comment="发布状态（published/withdrawn）"),
            sa.Column("operator_id", sa.BigInteger(), nullable=True, comment="操作人用户ID"),
            sa.Column("operator_name", sa.String(length=64), nullable=True, comment="操作人用户名"),
            sa.Column("sent_at", sa.DateTime(), nullable=True, comment="首次投递时间"),
            sa.Column("metadata_json", sa.JSON(), nullable=True, comment="扩展元数据"),
            sa.Column("published_at", sa.DateTime(), nullable=True, comment="发布时间"),
            sa.Column("withdrawn_at", sa.DateTime(), nullable=True, comment="撤回时间"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
            sa.PrimaryKeyConstraint("id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index("idx_notice_status", "system_notifications", ["status"])
        op.create_index("idx_notice_type", "system_notifications", ["notice_type"])
        op.create_index("idx_notice_created_at", "system_notifications", ["created_at"])
    else:
        # 1. system_notifications 加列（幂等：已存在则跳过）
        existing_columns = {c["name"] for c in sa.inspect(bind).get_columns("system_notifications")}
        if "event_type" not in existing_columns:
            op.add_column(
                "system_notifications",
                sa.Column(
                    "event_type",
                    sa.String(length=64),
                    nullable=False,
                    server_default="system.notice",
                    comment="事件类型（默认 system.notice）",
                ),
            )
        if "sent_at" not in existing_columns:
            op.add_column(
                "system_notifications",
                sa.Column("sent_at", sa.DateTime(), nullable=True, comment="首次投递时间"),
            )
        if "metadata_json" not in existing_columns:
            op.add_column(
                "system_notifications",
                sa.Column("metadata_json", sa.JSON(), nullable=True, comment="扩展元数据"),
            )

    # 2. 新建投递明细表（已存在则跳过，兼容 create_all 自动建表的历史库）
    if not _has_table(bind, "system_notice_delivery"):
        op.create_table(
            "system_notice_delivery",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("system_notification_id", sa.BigInteger(), nullable=True, comment="关联系统通知ID（非系统通知来源为空）"),
            sa.Column("source", sa.String(length=32), nullable=False, comment="通知来源（system_notice/station/alert/openapi_app）"),
            sa.Column("event_type", sa.String(length=64), nullable=False, comment="事件类型"),
            sa.Column("user_id", sa.BigInteger(), nullable=True, comment="目标用户ID（渠道级投递如告警webhook为空）"),
            sa.Column("channel", sa.String(length=32), nullable=False, comment="发送渠道"),
            sa.Column("recipient", sa.String(length=256), nullable=False, comment="接收人（发送时实际地址快照）"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", comment="发送状态"),
            sa.Column("retry_count", sa.BigInteger(), nullable=False, server_default=sa.text("0"), comment="已重试次数"),
            sa.Column("max_retries", sa.BigInteger(), nullable=False, server_default=sa.text("3"), comment="最大重试次数"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("receive_at", sa.DateTime(), nullable=True, comment="送达/接收时间"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
            sa.PrimaryKeyConstraint("id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index("idx_delivery_notification", "system_notice_delivery", ["system_notification_id"])
        op.create_index("idx_delivery_user", "system_notice_delivery", ["user_id"])
        op.create_index("idx_delivery_status_retry", "system_notice_delivery", ["status", "retry_count"])
        op.create_index("idx_delivery_created_at", "system_notice_delivery", ["created_at"])

    # 3. 新建站内信独立表（已存在则跳过，兼容 create_all 自动建表的历史库）
    if not _has_table(bind, "station_messages"):
        op.create_table(
            "station_messages",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("user_id", sa.BigInteger(), nullable=False, comment="接收用户ID"),
            sa.Column("operator_id", sa.BigInteger(), nullable=True, comment="发送人用户ID（系统自动为空）"),
            sa.Column("subject", sa.String(length=200), nullable=False, comment="消息标题"),
            sa.Column("content", sa.Text(), nullable=False, comment="消息正文"),
            sa.Column("source", sa.String(length=32), nullable=False, comment="消息来源（system_notice/station/alert/openapi_app）"),
            sa.Column("event_type", sa.String(length=64), nullable=True, comment="事件类型（前端跳转依据）"),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否已读"),
            sa.Column("read_at", sa.DateTime(), nullable=True, comment="阅读时间"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
            sa.PrimaryKeyConstraint("id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index("idx_station_user", "station_messages", ["user_id"])
        op.create_index("idx_station_user_read", "station_messages", ["user_id", "is_read"])
        op.create_index("idx_station_created_at", "station_messages", ["created_at"])

    # 4. 数据迁移：notification_records → delivery + station_messages
    if _has_table(bind, _OLD_TABLE):
        columns = [c["name"] for c in sa.inspect(bind).get_columns(_OLD_TABLE)]
        rows = bind.exec_driver_sql(
            f"SELECT id, event_type, channel, recipient, subject, content, status, "
            f"retry_count, max_retries, error_message, created_at, sent_at FROM `{_OLD_TABLE}`"
        ).fetchall()
        for row in rows:
            row_data: dict[str, Any] = {
                "id": row[0],
                "event_type": row[1],
                "channel": row[2],
                "recipient": row[3],
                "subject": row[4],
                "content": row[5],
                "status": row[6],
                "retry_count": row[7],
                "max_retries": row[8],
                "error_message": row[9],
                "created_at": row[10],
                "sent_at": row[11],
            }
            source = _map_source(row_data["event_type"])
            # 投递明细（全部记录）
            user_id = None
            match = _USER_RECIPIENT_RE.match(row_data["recipient"])
            if match is not None:
                user_id = int(match.group(1))
            bind.exec_driver_sql(
                "INSERT INTO `system_notice_delivery` "
                "(system_notification_id, source, event_type, user_id, channel, recipient, "
                "status, retry_count, max_retries, error_message, receive_at, created_at, updated_at) "
                "VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    source,
                    row_data["event_type"],
                    user_id,
                    row_data["channel"],
                    row_data["recipient"],
                    _normalize_status(row_data["status"]),
                    row_data["retry_count"],
                    row_data["max_retries"],
                    row_data["error_message"],
                    row_data["sent_at"],
                    row_data["created_at"],
                    row_data["created_at"],
                ),
            )
            # 站内信收件箱（channel=station 且接收人为 user:{id}）
            if row_data["channel"] == "station" and match is not None:
                bind.exec_driver_sql(
                    "INSERT INTO `station_messages` "
                    "(user_id, subject, content, source, event_type, is_read, read_at, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        user_id,
                        row_data["subject"],
                        row_data["content"],
                        source,
                        row_data["event_type"],
                        1 if row_data["status"] == "read" else 0,
                        None,
                        row_data["created_at"],
                    ),
                )
        op.drop_table(_OLD_TABLE)


def downgrade() -> None:
    # 重建 notification_records（结构快照，不做数据回迁）
    op.create_table(
        _OLD_TABLE,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("event_type", sa.String(length=64), nullable=False, comment="事件类型"),
        sa.Column("channel", sa.String(length=32), nullable=False, comment="发送渠道"),
        sa.Column("recipient", sa.String(length=256), nullable=False, comment="接收人"),
        sa.Column("subject", sa.String(length=200), nullable=False, comment="通知主题"),
        sa.Column("content", sa.Text(), nullable=False, comment="渲染后正文"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", comment="发送状态"),
        sa.Column("retry_count", sa.BigInteger(), nullable=False, server_default=sa.text("0"), comment="已重试次数"),
        sa.Column("max_retries", sa.BigInteger(), nullable=False, server_default=sa.text("3"), comment="最大重试次数"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("metadata_json", sa.JSON(), nullable=True, comment="扩展元数据"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("sent_at", sa.DateTime(), nullable=True, comment="发送时间"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.drop_table("station_messages")
    op.drop_table("system_notice_delivery")
    for column in ("event_type", "sent_at", "metadata_json"):
        op.drop_column("system_notifications", column)
