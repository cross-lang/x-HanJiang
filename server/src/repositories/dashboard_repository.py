#!/usr/bin/env python3
"""
仪表盘数据访问实现
本模块提供仪表盘统计查询 Repository，跨多张实体表做只读聚合查询。
仅负责数据查询（依赖实体模型），统计口径与结果组装由 Service 层负责。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    Entity → Schema 的转换由 Service 层完成。

Classes:
    DashboardRepository: 仪表盘统计查询实现
"""

from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.constants.enums import AppStatus, CommonStatus, LoginStatus, UserStatus
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.models.entities.audit_entity import AuditLogEntity
from src.models.entities.developer_entity import DeveloperEntity
from src.models.entities.file_entity import FileEntity
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.notification_delivery_entity import NotificationDeliveryEntity
from src.models.entities.user_entity import RoleEntity, UserEntity, UserRoleEntity


class DashboardRepository:
    """仪表盘统计查询（只读聚合，不提供写操作）。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── 关键指标 ──────────────────────────────────────────

    def card_counts(self) -> tuple[int, int, int]:
        """统计活跃用户数、启用角色数、活跃应用数。"""
        user_count = (
            self._session.execute(
                select(func.count(UserEntity.id)).where(
                    UserEntity.status == UserStatus.ENABLED.value,
                    UserEntity.deleted_at.is_(None),
                )
            ).scalar()
            or 0
        )
        role_count = (
            self._session.execute(
                select(func.count(RoleEntity.id)).where(
                    RoleEntity.status == CommonStatus.ENABLED.value,
                    RoleEntity.deleted_at.is_(None),
                )
            ).scalar()
            or 0
        )
        app_count = (
            self._session.execute(
                select(func.count(OpenApiAppEntity.id)).where(
                    OpenApiAppEntity.status == AppStatus.ACTIVE.value,
                    OpenApiAppEntity.deleted_at.is_(None),
                )
            ).scalar()
            or 0
        )
        return user_count, role_count, app_count

    def today_login_count(self, day: date) -> int:
        """统计指定日期登录次数。"""
        return (
            self._session.execute(
                select(func.count(LoginLogEntity.id)).where(func.date(LoginLogEntity.created_at) == day)
            ).scalar()
            or 0
        )

    # ── 趋势 ──────────────────────────────────────────────

    def login_trend(self, start_date: date) -> list:
        """近 N 天登录趋势（按日分组）。"""
        return self._session.execute(
            select(
                func.date(LoginLogEntity.created_at).label("date"),
                func.count(LoginLogEntity.id).label("count"),
            )
            .where(func.date(LoginLogEntity.created_at) >= start_date)
            .group_by(func.date(LoginLogEntity.created_at))
            .order_by(func.date(LoginLogEntity.created_at))
        ).all()

    def audit_trend(self, start_date: date) -> list:
        """近 N 天操作日志趋势（按日分组）。"""
        return self._session.execute(
            select(
                func.date(AuditLogEntity.created_at).label("date"),
                func.count(AuditLogEntity.id).label("count"),
            )
            .where(func.date(AuditLogEntity.created_at) >= start_date)
            .group_by(func.date(AuditLogEntity.created_at))
            .order_by(func.date(AuditLogEntity.created_at))
        ).all()

    def login_failed_trend(self, start_date: date) -> list:
        """近 N 天登录失败趋势（按日分组）。"""
        return self._session.execute(
            select(
                func.date(LoginLogEntity.created_at).label("date"),
                func.count(LoginLogEntity.id).label("count"),
            )
            .where(func.date(LoginLogEntity.created_at) >= start_date)
            .where(LoginLogEntity.status == LoginStatus.FAILED.mark)
            .group_by(func.date(LoginLogEntity.created_at))
        ).all()

    def new_users_trend(self, start_date: date) -> list:
        """近 N 天新增用户趋势（按日分组）。"""
        return self._session.execute(
            select(
                func.date(UserEntity.created_at).label("date"),
                func.count(UserEntity.id).label("count"),
            )
            .where(func.date(UserEntity.created_at) >= start_date)
            .group_by(func.date(UserEntity.created_at))
        ).all()

    def notify_status_trend(self, start_date: date) -> list:
        """近 N 天通知投递状态趋势（按日+状态分组）。"""
        return self._session.execute(
            select(
                func.date(NotificationDeliveryEntity.created_at).label("date"),
                NotificationDeliveryEntity.status,
                func.count(NotificationDeliveryEntity.id).label("count"),
            )
            .where(func.date(NotificationDeliveryEntity.created_at) >= start_date)
            .group_by(
                func.date(NotificationDeliveryEntity.created_at),
                NotificationDeliveryEntity.status,
            )
        ).all()

    # ── 分布 ──────────────────────────────────────────────

    def role_distribution(self) -> list:
        """用户角色分布（角色名 + 关联用户数）。"""
        return self._session.execute(
            select(
                RoleEntity.role_name,
                func.count(UserRoleEntity.user_id).label("count"),
            )
            .join(UserRoleEntity, UserRoleEntity.role_id == RoleEntity.id)
            .group_by(RoleEntity.id, RoleEntity.role_name)
        ).all()

    def user_status_distribution(self) -> list:
        """用户状态分布。"""
        return self._session.execute(
            select(UserEntity.status, func.count(UserEntity.id).label("count")).group_by(UserEntity.status)
        ).all()

    def notify_channel_distribution(self) -> list:
        """通知投递渠道分布。"""
        return self._session.execute(
            select(
                NotificationDeliveryEntity.channel,
                func.count(NotificationDeliveryEntity.id).label("count"),
            ).group_by(NotificationDeliveryEntity.channel)
        ).all()

    # ── 最近记录 ──────────────────────────────────────────

    def recent_logins(self, limit: int = 10) -> list:
        """最近登录记录（关联用户名，按时间倒序）。"""
        return self._session.execute(
            select(LoginLogEntity, UserEntity.username, UserEntity.name)
            .outerjoin(UserEntity, UserEntity.id == LoginLogEntity.user_id)
            .order_by(LoginLogEntity.created_at.desc())
            .limit(limit)
        ).all()

    def recent_audits(self, limit: int = 10) -> list:
        """最近操作日志（按时间倒序，关联用户名）。"""
        return list(
            self._session.execute(
                select(AuditLogEntity, UserEntity.username, UserEntity.name)
                .outerjoin(UserEntity, UserEntity.id == AuditLogEntity.operator_id)
                .order_by(AuditLogEntity.created_at.desc())
                .limit(limit)
            ).all()
        )

    def my_logins(self, user_id: int, limit: int = 10) -> list[LoginLogEntity]:
        """指定用户的最近登录记录。"""
        return list(
            self._session.execute(
                select(LoginLogEntity)
                .where(LoginLogEntity.user_id == user_id)
                .order_by(LoginLogEntity.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def my_audits(self, user_id: int, limit: int = 10) -> list[AuditLogEntity]:
        """指定用户的最近操作日志。"""
        return list(
            self._session.execute(
                select(AuditLogEntity)
                .where(AuditLogEntity.operator_id == user_id)
                .order_by(AuditLogEntity.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

    # ── 开放平台统计 ──────────────────────────────────────

    def openapi_app_status_distribution(self) -> list:
        """开放应用状态分布（按 active/disabled 分组，排除已删除）。"""
        return self._session.execute(
            select(
                OpenApiAppEntity.status,
                func.count(OpenApiAppEntity.id).label("count"),
            )
            .where(OpenApiAppEntity.deleted_at.is_(None))
            .group_by(OpenApiAppEntity.status)
        ).all()

    def openapi_developer_count(self) -> int:
        """启用状态的开发者账号总数。"""
        return (
            self._session.execute(
                select(func.count(DeveloperEntity.id)).where(DeveloperEntity.status == CommonStatus.ENABLED.value)
            ).scalar()
            or 0
        )

    def openapi_registration_status_distribution(self) -> list:
        """应用申请审批状态分布（按 pending/approved/rejected 分组）。"""
        return self._session.execute(
            select(
                OpenApiAppRegistrationEntity.status,
                func.count(OpenApiAppRegistrationEntity.id).label("count"),
            ).group_by(OpenApiAppRegistrationEntity.status)
        ).all()

    def openapi_registration_trend(self, start_date: date) -> list:
        """近 N 天应用申请提交趋势（按 created_at 日分组）。"""
        return self._session.execute(
            select(
                func.date(OpenApiAppRegistrationEntity.created_at).label("date"),
                func.count(OpenApiAppRegistrationEntity.id).label("count"),
            )
            .where(func.date(OpenApiAppRegistrationEntity.created_at) >= start_date)
            .group_by(func.date(OpenApiAppRegistrationEntity.created_at))
            .order_by(func.date(OpenApiAppRegistrationEntity.created_at))
        ).all()

    def openapi_registration_review_trend(self, start_date: date) -> list:
        """近 N 天应用申请审批处理趋势（按 approved_at 日分组，含通过与驳回）。"""
        return self._session.execute(
            select(
                func.date(OpenApiAppRegistrationEntity.approved_at).label("date"),
                func.count(OpenApiAppRegistrationEntity.id).label("count"),
            )
            .where(
                OpenApiAppRegistrationEntity.approved_at.is_not(None),
                func.date(OpenApiAppRegistrationEntity.approved_at) >= start_date,
            )
            .group_by(func.date(OpenApiAppRegistrationEntity.approved_at))
            .order_by(func.date(OpenApiAppRegistrationEntity.approved_at))
        ).all()

    def recent_openapi_registrations(self, limit: int = 6) -> list:
        """最近应用申请记录（按提交时间倒序，关联归属人姓名）。

        Returns:
            list: (注册批次, owner_type, 开发者姓名, 管理员姓名) 行列表。
        """
        return self._session.execute(
            select(
                OpenApiAppRegistrationEntity,
                OpenApiAppEntity.owner_type,
                DeveloperEntity.name.label("dev_name"),
                UserEntity.name.label("admin_name"),
            )
            .join(OpenApiAppEntity, OpenApiAppEntity.id == OpenApiAppRegistrationEntity.app_id)
            .outerjoin(
                DeveloperEntity,
                and_(
                    OpenApiAppEntity.owner_type == "developer",
                    OpenApiAppEntity.owner_id == DeveloperEntity.id,
                ),
            )
            .outerjoin(
                UserEntity,
                and_(
                    OpenApiAppEntity.owner_type == "admin",
                    OpenApiAppEntity.owner_id == UserEntity.id,
                ),
            )
            .order_by(OpenApiAppRegistrationEntity.created_at.desc())
            .limit(limit)
        ).all()

    # ── 存储用量 ──────────────────────────────────────────

    def storage_stats(self) -> tuple[int, int, list]:
        """存储用量统计。

        Returns:
            tuple[int, int, list]: (总大小, 总数, 按文件夹行列表[(folder, count, size)])
        """
        total_size = (
            self._session.execute(
                select(func.coalesce(func.sum(FileEntity.size_bytes), 0)).where(
                    FileEntity.is_deleted == False  # noqa: E712
                )
            ).scalar()
            or 0
        )
        total_count = (
            self._session.execute(
                select(func.count(FileEntity.id)).where(
                    FileEntity.is_deleted == False  # noqa: E712
                )
            ).scalar()
            or 0
        )
        by_folder = self._session.execute(
            select(
                FileEntity.folder,
                func.count(FileEntity.id).label("count"),
                func.coalesce(func.sum(FileEntity.size_bytes), 0).label("size"),
            )
            .where(FileEntity.is_deleted == False)  # noqa: E712
            .group_by(FileEntity.folder)
        ).all()
        return total_size, total_count, by_folder
