#!/usr/bin/env python3
"""仪表盘统计服务。"""

from datetime import datetime, timedelta, UTC

from sqlalchemy import func, select

from src.infras.database import get_cached_database_provider
from src.models.entities.user_entity import UserEntity, RoleEntity, UserRoleEntity
from src.models.entities.audit_entity import AuditLogEntity
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.notification_entity import NotificationRecordEntity
from src.models.entities.file_entity import FileEntity


class DashboardService:
    """仪表盘统计服务，汇总用户、角色、应用、登录趋势等数据。"""

    def __init__(self):
        self._session = get_cached_database_provider().get_session_factory()()

    def get_stats(self) -> dict:
        """获取仪表盘全部统计数据。"""
        try:
            today = datetime.now(UTC).date()
            week_ago = today - timedelta(days=6)

            # 关键指标
            user_count = self._session.execute(
                select(func.count(UserEntity.id)).where(UserEntity.status == "active", UserEntity.deleted_at.is_(None))
            ).scalar() or 0
            role_count = self._session.execute(
                select(func.count(RoleEntity.id)).where(RoleEntity.status == "enabled", RoleEntity.deleted_at.is_(None))
            ).scalar() or 0
            app_count = self._session.execute(
                select(func.count(OpenApiAppEntity.id)).where(OpenApiAppEntity.status == "active", OpenApiAppEntity.deleted_at.is_(None))
            ).scalar() or 0

            # 今日登录数
            today_login = self._session.execute(
                select(func.count(LoginLogEntity.id)).where(
                    func.date(LoginLogEntity.created_at) == today
                )
            ).scalar() or 0

            # 近7天登录趋势
            login_trend = self._session.execute(
                select(
                    func.date(LoginLogEntity.created_at).label("date"),
                    func.count(LoginLogEntity.id).label("count"),
                )
                .where(func.date(LoginLogEntity.created_at) >= week_ago)
                .group_by(func.date(LoginLogEntity.created_at))
                .order_by(func.date(LoginLogEntity.created_at))
            ).all()
            all_dates = [(week_ago + timedelta(days=i)).isoformat() for i in range(7)]
            login_trend_map = {str(r.date): r.count for r in login_trend}
            login_counts = [login_trend_map.get(d, 0) for d in all_dates]

            # 近7天操作日志趋势
            audit_trend = self._session.execute(
                select(
                    func.date(AuditLogEntity.created_at).label("date"),
                    func.count(AuditLogEntity.id).label("count"),
                )
                .where(func.date(AuditLogEntity.created_at) >= week_ago)
                .group_by(func.date(AuditLogEntity.created_at))
                .order_by(func.date(AuditLogEntity.created_at))
            ).all()
            audit_trend_map = {str(r.date): r.count for r in audit_trend}
            audit_counts = [audit_trend_map.get(d, 0) for d in all_dates]

            # 用户角色分布
            role_dist = self._session.execute(
                select(
                    RoleEntity.role_name,
                    func.count(UserRoleEntity.user_id).label("count"),
                )
                .join(UserRoleEntity, UserRoleEntity.role_id == RoleEntity.id)
                .group_by(RoleEntity.id, RoleEntity.role_name)
            ).all()
            role_distribution = [{"name": r.role_name, "value": r.count} for r in role_dist]

            # 最近登录记录
            recent_logins = self._session.execute(
                select(LoginLogEntity, UserEntity.username)
                .outerjoin(UserEntity, UserEntity.id == LoginLogEntity.user_id)
                .order_by(LoginLogEntity.created_at.desc()).limit(10)
            ).all()
            recent_logins_list = [
                {
                    "id": r[0].id,
                    "username": r[1] or "-",
                    "ip_address": r[0].ip_address,
                    "status": r[0].status,
                    "created_at": r[0].created_at.isoformat() if r[0].created_at else None,
                }
                for r in recent_logins
            ]

            # 最近操作日志
            recent_audits = self._session.execute(
                select(AuditLogEntity).order_by(AuditLogEntity.created_at.desc()).limit(10)
            ).scalars().all()
            recent_audits_list = [
                {
                    "id": r.id,
                    "entity_type": r.entity_type,
                    "action": r.action,
                    "operator_name": r.operator_name,
                    "ip_address": r.ip_address,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in recent_audits
            ]

            # 用户状态分布
            user_status_rows = self._session.execute(
                select(UserEntity.status, func.count(UserEntity.id).label("count"))
                .group_by(UserEntity.status)
            ).all()
            status_label_map = {"active": "活跃", "inactive": "禁用", "locked": "锁定"}
            user_status_distribution = [
                {"name": status_label_map.get(r.status, r.status), "value": r.count}
                for r in user_status_rows
            ]

            # 近30天新增用户趋势
            month_ago = today - timedelta(days=29)
            new_users_rows = self._session.execute(
                select(
                    func.date(UserEntity.created_at).label("date"),
                    func.count(UserEntity.id).label("count"),
                )
                .where(func.date(UserEntity.created_at) >= month_ago)
                .group_by(func.date(UserEntity.created_at))
            ).all()
            all_month_dates = [(month_ago + timedelta(days=i)).isoformat() for i in range(30)]
            new_users_map = {str(r.date): r.count for r in new_users_rows}
            new_users_counts = [new_users_map.get(d, 0) for d in all_month_dates]

            # 近7天登录失败趋势
            login_failed_rows = self._session.execute(
                select(
                    func.date(LoginLogEntity.created_at).label("date"),
                    func.count(LoginLogEntity.id).label("count"),
                )
                .where(func.date(LoginLogEntity.created_at) >= week_ago)
                .where(LoginLogEntity.status == "failed")
                .group_by(func.date(LoginLogEntity.created_at))
            ).all()
            login_failed_map = {str(r.date): r.count for r in login_failed_rows}
            login_failed_counts = [login_failed_map.get(d, 0) for d in all_dates]

            # 通知渠道分布
            channel_rows = self._session.execute(
                select(NotificationRecordEntity.channel, func.count(NotificationRecordEntity.id).label("count"))
                .group_by(NotificationRecordEntity.channel)
            ).all()
            channel_distribution = [
                {"name": r.channel, "value": r.count} for r in channel_rows
            ]

            # 通知发送成功率趋势（近7天）
            notify_status_rows = self._session.execute(
                select(
                    func.date(NotificationRecordEntity.created_at).label("date"),
                    NotificationRecordEntity.status,
                    func.count(NotificationRecordEntity.id).label("count"),
                )
                .where(func.date(NotificationRecordEntity.created_at) >= week_ago)
                .group_by(func.date(NotificationRecordEntity.created_at), NotificationRecordEntity.status)
            ).all()
            notify_success_map: dict[str, int] = {}
            notify_failed_map: dict[str, int] = {}
            for r in notify_status_rows:
                d = str(r.date)
                if r.status == "sent":
                    notify_success_map[d] = r.count
                elif r.status in ("failed", "pending"):
                    notify_failed_map[d] = notify_failed_map.get(d, 0) + r.count
            notify_success_counts = [notify_success_map.get(d, 0) for d in all_dates]
            notify_failed_counts = [notify_failed_map.get(d, 0) for d in all_dates]

            # 存储用量统计
            storage_total_size = self._session.execute(
                select(func.coalesce(func.sum(FileEntity.size_bytes), 0)).where(
                    FileEntity.is_deleted == False
                )
            ).scalar() or 0
            storage_total_count = self._session.execute(
                select(func.count(FileEntity.id)).where(FileEntity.is_deleted == False)
            ).scalar() or 0
            storage_by_folder = self._session.execute(
                select(FileEntity.folder, func.count(FileEntity.id).label("count"), func.coalesce(func.sum(FileEntity.size_bytes), 0).label("size"))
                .where(FileEntity.is_deleted == False)
                .group_by(FileEntity.folder)
            ).all()
            storage_usage = {
                "total_size_bytes": storage_total_size,
                "total_count": storage_total_count,
                "by_folder": [{"folder": r.folder, "count": r.count, "size_bytes": r.size} for r in storage_by_folder],
            }

            return {
                "cards": {
                    "user_count": user_count,
                    "role_count": role_count,
                    "app_count": app_count,
                    "today_login": today_login,
                },
                "login_trend": {"dates": all_dates, "counts": login_counts},
                "audit_trend": {"dates": all_dates, "counts": audit_counts},
                "role_distribution": role_distribution,
                "recent_logins": recent_logins_list,
                "recent_audits": recent_audits_list,
                "user_status_distribution": user_status_distribution,
                "new_users_trend": {"dates": all_month_dates, "counts": new_users_counts},
                "login_failed_trend": {"dates": all_dates, "counts": login_failed_counts},
                "notify_channel_distribution": channel_distribution,
                "notify_trend": {
                    "dates": all_dates,
                    "success": notify_success_counts,
                    "failed": notify_failed_counts,
                },
                "storage_usage": storage_usage,
            }
        finally:
            self._session.close()

    def get_my_activity(self, user_id: int) -> dict:
        """获取当前用户的最近登录日志和操作日志（首页用）。"""
        try:
            # 当前用户最近登录记录
            my_logins = self._session.execute(
                select(LoginLogEntity)
                .where(LoginLogEntity.user_id == user_id)
                .order_by(LoginLogEntity.created_at.desc())
                .limit(10)
            ).scalars().all()
            my_logins_list = [
                {
                    "id": r.id,
                    "ip_address": r.ip_address,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in my_logins
            ]

            # 当前用户最近操作日志
            my_audits = self._session.execute(
                select(AuditLogEntity)
                .where(AuditLogEntity.operator_id == user_id)
                .order_by(AuditLogEntity.created_at.desc())
                .limit(10)
            ).scalars().all()
            my_audits_list = [
                {
                    "id": r.id,
                    "entity_type": r.entity_type,
                    "action": r.action,
                    "ip_address": r.ip_address,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in my_audits
            ]

            return {
                "recent_logins": my_logins_list,
                "recent_audits": my_audits_list,
            }
        finally:
            self._session.close()
