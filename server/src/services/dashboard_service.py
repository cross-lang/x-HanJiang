#!/usr/bin/env python3
"""仪表盘统计服务。
仅调用 DashboardRepository 获取原始统计行，负责结果组装；
不直接操作数据库会话、不编写 SQL。
"""

from datetime import UTC, datetime, timedelta

from src.constants.enums import NotificationStatus
from src.repositories.dashboard_repository import DashboardRepository


class DashboardService:
    """仪表盘统计服务，汇总用户、角色、应用、登录趋势等数据。"""

    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def get_stats(self) -> dict:
        """获取仪表盘全部统计数据。"""
        today = datetime.now(UTC).date()
        week_ago = today - timedelta(days=6)
        month_ago = today - timedelta(days=29)
        # 关键指标
        user_count, role_count, app_count = self._repository.card_counts()
        # 今日登录数
        today_login = self._repository.today_login_count(today)
        # 近7天登录趋势
        login_trend = self._repository.login_trend(week_ago)
        all_dates = [(week_ago + timedelta(days=i)).isoformat() for i in range(7)]
        login_trend_map = {str(r.date): r.count for r in login_trend}
        login_counts = [login_trend_map.get(d, 0) for d in all_dates]
        # 近7天操作日志趋势
        audit_trend = self._repository.audit_trend(week_ago)
        audit_trend_map = {str(r.date): r.count for r in audit_trend}
        audit_counts = [audit_trend_map.get(d, 0) for d in all_dates]
        # 用户角色分布
        role_dist = self._repository.role_distribution()
        role_distribution = [{"name": r.role_name, "value": r.count} for r in role_dist]
        # 最近登录记录
        recent_logins = self._repository.recent_logins(10)
        recent_logins_list = [
            {
                "id": r[0].id,
                "username": r[1] or "-",
                "name": r[2] or "",
                "ip_address": r[0].ip_address,
                "status": r[0].status,
                "created_at": r[0].created_at.isoformat() if r[0].created_at else None,
            }
            for r in recent_logins
        ]
        # 最近操作日志
        recent_audits = self._repository.recent_audits(10)
        recent_audits_list = [
            {
                "id": r[0].id,
                "entity_type": r[0].entity_type,
                "action": r[0].action,
                "operator_username": r[1] or "-",
                "operator_name": r[2] or "",
                "ip_address": r[0].ip_address,
                "created_at": r[0].created_at.isoformat() if r[0].created_at else None,
            }
            for r in recent_audits
        ]
        # 用户状态分布
        user_status_rows = self._repository.user_status_distribution()
        status_label_map = {"enabled": "启用", "disabled": "禁用"}
        user_status_distribution = [
            {"name": status_label_map.get(r.status, r.status), "value": r.count} for r in user_status_rows
        ]
        # 近30天新增用户趋势
        new_users_rows = self._repository.new_users_trend(month_ago)
        all_month_dates = [(month_ago + timedelta(days=i)).isoformat() for i in range(30)]
        new_users_map = {str(r.date): r.count for r in new_users_rows}
        new_users_counts = [new_users_map.get(d, 0) for d in all_month_dates]
        # 近7天登录失败趋势
        login_failed_rows = self._repository.login_failed_trend(week_ago)
        login_failed_map = {str(r.date): r.count for r in login_failed_rows}
        login_failed_counts = [login_failed_map.get(d, 0) for d in all_dates]
        # 通知渠道分布
        channel_rows = self._repository.notify_channel_distribution()
        channel_distribution = [{"name": r.channel, "value": r.count} for r in channel_rows]
        # 通知发送成功率趋势（近7天）
        notify_status_rows = self._repository.notify_status_trend(week_ago)
        notify_success_map: dict[str, int] = {}
        notify_failed_map: dict[str, int] = {}
        for r in notify_status_rows:
            d = str(r.date)
            if r.status == NotificationStatus.SUCCESS.value:
                notify_success_map[d] = r.count
            elif r.status in (NotificationStatus.FAILED.value, NotificationStatus.PENDING.value):
                notify_failed_map[d] = notify_failed_map.get(d, 0) + r.count
        notify_success_counts = [notify_success_map.get(d, 0) for d in all_dates]
        notify_failed_counts = [notify_failed_map.get(d, 0) for d in all_dates]
        # 存储用量统计
        storage_total_size, storage_total_count, storage_by_folder = self._repository.storage_stats()
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

    def get_my_activity(self, user_id: int) -> dict:
        """获取当前用户的最近登录日志和操作日志（首页用）。"""
        my_logins = self._repository.my_logins(user_id, 10)
        my_logins_list = [
            {
                "id": r.id,
                "ip_address": r.ip_address,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in my_logins
        ]
        my_audits = self._repository.my_audits(user_id, 10)
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
