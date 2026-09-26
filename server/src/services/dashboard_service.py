#!/usr/bin/env python3
"""仪表盘统计服务。"""

from datetime import datetime, timedelta, UTC

from sqlalchemy import func, select

from src.infras.database import get_cached_database_provider
from src.models.entities.user_entity import UserEntity, RoleEntity, UserRoleEntity
from src.models.entities.audit_entity import AuditLogEntity
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.app_entity import OpenApiAppEntity


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
            user_count = self._session.execute(select(func.count(UserEntity.id))).scalar() or 0
            role_count = self._session.execute(select(func.count(RoleEntity.id))).scalar() or 0
            app_count = self._session.execute(select(func.count(OpenApiAppEntity.id))).scalar() or 0

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
            }
        finally:
            self._session.close()
