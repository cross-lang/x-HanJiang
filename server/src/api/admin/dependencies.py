#!/usr/bin/env python3
"""
管理系统（admin 域）FastAPI 依赖注入模块。

本文件承载管理后台（/api/admin/v1）的全部依赖工厂：
- 权限/审计/告警/仪表盘/公告/站内信/菜单/个人中心/AI 助手等服务工厂
- 管理端会话鉴权族（get_current_user / require_user_role / require_user_permission 等）

跨域公共依赖（get_db_session / get_notification_dispatcher / _bearer_scheme 及
用户/角色/文件共享服务工厂 get_user_service / get_role_service / get_file_service）
位于 src/api/dependencies.py；开放接口域见 src/api/open/dependencies.py；
开放平台门户域见 src/api/open_portal/dependencies.py。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.api.dependencies import _bearer_scheme, get_db_session, get_notification_dispatcher
from src.constants.enums import SystemRoleCode
from src.core.exceptions import AuthorizationException
from src.schemas.admin.auth import CurrentUser
from src.services.admin.alert_service import AlertService
from src.services.admin.audit_service import AuditService
from src.services.admin.auth_service import AuthService
from src.services.admin.health_service import HealthService
from src.services.admin.permission_service import PermissionService

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher
    from src.repositories.assistant_repository import (
        AssistantConversationRepository,
        AssistantFeedbackRepository,
        AssistantMessageRepository,
    )
    from src.repositories.login_log_repository import LoginLogRepository
    from src.repositories.menu_repository import MenuRepository
    from src.repositories.notification_config_repository import UserNotificationConfigRepository
    from src.repositories.permission_repository import PermissionRepository
    from src.repositories.role_permission_repository import RolePermissionRepository
    from src.repositories.role_repository import RoleRepository
    from src.repositories.user_repository import UserRepository
    from src.services.admin.announcement_service import AnnouncementService
    from src.services.admin.assistant_service import AssistantService
    from src.services.admin.dashboard_service import DashboardService
    from src.services.admin.developer_admin_service import DeveloperAdminService
    from src.services.admin.login_log_service import LoginLogService
    from src.services.admin.openapi_app_registration_service import (
        OpenApiAppRegistrationService,
    )
    from src.services.admin.openapi_app_service import OpenApiAppService
    from src.services.admin.profile_service import ProfileService
    from src.services.admin.search_service import SearchService
    from src.services.admin.station_service import StationMessageService
    from src.services.admin.system_monitor_service import SystemMonitorService
    from src.services.admin.system_notification_config_service import SystemNotificationConfigService
    from src.services.admin.system_notification_service import SystemNotificationService



def get_user_repository(
    db_session: Session = Depends(get_db_session),
) -> UserRepository:
    """获取用户仓库实例（可被 DI 容器覆盖）。"""
    from src.repositories.user_repository import UserRepository

    return UserRepository(session=db_session)


def get_login_log_repository(
    db_session: Session = Depends(get_db_session),
) -> LoginLogRepository:
    """获取登录日志仓库实例。"""
    from src.repositories.login_log_repository import LoginLogRepository

    return LoginLogRepository(session=db_session)


def get_role_repository(
    db_session: Session = Depends(get_db_session),
) -> RoleRepository:
    """获取角色仓库实例。"""
    from src.repositories.role_repository import RoleRepository

    return RoleRepository(session=db_session)


def get_alert_service(
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    db_session: Session = Depends(get_db_session),
) -> AlertService:
    """获取告警服务实例。"""
    return AlertService(dispatcher=dispatcher, session=db_session)


def get_health_service() -> HealthService:
    """获取健康检查服务（下游探测与告警编排在 service 层）。"""
    from src.services.admin.health_service import HealthService

    return HealthService()


def get_announcement_service(
    db_session: Session = Depends(get_db_session),
) -> AnnouncementService:
    """获取公告业务服务实例。"""
    from src.repositories.announcement_repository import AnnouncementRepository
    from src.services.admin.announcement_service import AnnouncementService

    return AnnouncementService(repository=AnnouncementRepository(session=db_session))


def get_system_notification_service(
    db_session: Session = Depends(get_db_session),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> SystemNotificationService:
    """获取系统通知（广播）业务服务实例。"""
    from src.repositories.notification_delivery_repository import NotificationDeliveryRepository
    from src.repositories.role_repository import RoleRepository
    from src.repositories.station_message_repository import StationMessageRepository
    from src.repositories.system_notification_repository import SystemNotificationRepository
    from src.repositories.user_repository import UserRepository
    from src.services.admin.station_service import StationMessageService
    from src.services.admin.system_notification_service import SystemNotificationService

    return SystemNotificationService(
        notice_repository=SystemNotificationRepository(session=db_session),
        user_repository=UserRepository(session=db_session),
        role_repository=RoleRepository(session=db_session),
        station_service=StationMessageService(repository=StationMessageRepository(session=db_session)),
        dispatcher=dispatcher,
        delivery_repository=NotificationDeliveryRepository(session=db_session),
    )


def get_audit_service(
    db_session: Session = Depends(get_db_session),
) -> AuditService:
    """获取审计服务。"""
    from src.repositories.audit_log_repository import AuditLogRepository

    return AuditService(audit_log_repository=AuditLogRepository(session=db_session))


def get_dashboard_service(
    db_session: Session = Depends(get_db_session),
) -> DashboardService:
    """获取仪表盘统计服务。"""
    from src.repositories.dashboard_repository import DashboardRepository
    from src.services.admin.dashboard_service import DashboardService

    return DashboardService(repository=DashboardRepository(session=db_session))


def get_system_notification_config_service(
    db_session: Session = Depends(get_db_session),
) -> SystemNotificationConfigService:
    """获取系统通知配置服务。"""
    from src.repositories.system_notification_config_repository import (
        SystemNotificationConfigRepository,
    )
    from src.services.admin.system_notification_config_service import SystemNotificationConfigService

    return SystemNotificationConfigService(repository=SystemNotificationConfigRepository(session=db_session))


def get_system_monitor_service() -> SystemMonitorService:
    """获取系统运行监控服务（无状态，不依赖 DB 会话）。"""
    from src.services.admin.system_monitor_service import SystemMonitorService

    return SystemMonitorService()


def get_permission_repository(
    db_session: Session = Depends(get_db_session),
) -> PermissionRepository:
    """获取权限仓库实例。"""
    from src.repositories.permission_repository import PermissionRepository

    return PermissionRepository(session=db_session)


def get_role_permission_repository(
    db_session: Session = Depends(get_db_session),
) -> RolePermissionRepository:
    """获取角色权限关联仓库实例。"""
    from src.repositories.role_permission_repository import RolePermissionRepository

    return RolePermissionRepository(session=db_session)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    login_log_repository: LoginLogRepository = Depends(get_login_log_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> AuthService:
    """获取认证服务。"""
    return AuthService(
        user_repository=user_repository,
        role_repository=role_repository,
        login_log_repository=login_log_repository,
        dispatcher=dispatcher,
    )


def get_permission_service(
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    role_permission_repository: RolePermissionRepository = Depends(get_role_permission_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> PermissionService:
    """使用当前请求的 Repository 创建权限服务。"""
    from src.services.admin.permission_service import PermissionService

    return PermissionService(
        permission_repository=permission_repository,
        role_permission_repository=role_permission_repository,
        role_repository=role_repository,
        user_repository=user_repository,
        dispatcher=dispatcher,
    )


def get_login_log_service(
    login_log_repository: LoginLogRepository = Depends(get_login_log_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> LoginLogService:
    """使用当前请求的 Repository 创建登录日志服务。"""
    from src.services.admin.login_log_service import LoginLogService

    return LoginLogService(
        login_log_repository=login_log_repository,
        user_repository=user_repository,
    )


def get_openapi_app_service(
    db_session: Session = Depends(get_db_session),
) -> OpenApiAppService:
    """创建开放平台应用管理服务（管理端 CRUD/scope 授权/启停）。"""
    from src.repositories.openapi_app_registration_repository import (
        OpenApiAppRegistrationRepository,
    )
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.admin.openapi_app_service import OpenApiAppService

    return OpenApiAppService(
        repo=OpenApiAppRepository(session=db_session),
        registration_repo=OpenApiAppRegistrationRepository(session=db_session),
    )


def get_openapi_app_registration_service(
    db_session: Session = Depends(get_db_session),
) -> OpenApiAppRegistrationService:
    """创建开放平台应用审批服务（管理端申请批次列表/审批）。"""
    from src.repositories.openapi_app_registration_repository import (
        OpenApiAppRegistrationRepository,
    )
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.admin.openapi_app_registration_service import (
        OpenApiAppRegistrationService,
    )

    return OpenApiAppRegistrationService(
        repo=OpenApiAppRegistrationRepository(session=db_session),
        app_repo=OpenApiAppRepository(session=db_session),
    )


def get_developer_admin_service(
    db_session: Session = Depends(get_db_session),
) -> DeveloperAdminService:
    """创建开放平台开发者用户管理服务（管理端查询）。"""
    from src.repositories.developer_repository import DeveloperRepository
    from src.repositories.openapi_app_registration_repository import (
        OpenApiAppRegistrationRepository,
    )
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.admin.developer_admin_service import DeveloperAdminService
    from src.services.admin.openapi_app_service import OpenApiAppService

    return DeveloperAdminService(
        repository=DeveloperRepository(session=db_session),
        openapi_app_service=OpenApiAppService(
            repo=OpenApiAppRepository(session=db_session),
            registration_repo=OpenApiAppRegistrationRepository(session=db_session),
        ),
    )


def get_search_service(
    db_session: Session = Depends(get_db_session),
) -> SearchService:
    """获取搜索服务。"""
    from src.repositories.search_repository import SearchRepository
    from src.services.admin.search_service import SearchService

    return SearchService(repository=SearchRepository(session=db_session))


# ============================================================

# 管理端会话鉴权

# ============================================================


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    """解析 Bearer 令牌，返回当前登录用户."""
    token = credentials.credentials if credentials is not None else None
    return auth_service.get_current_user(token)


def require_user_role(role_code: str) -> Callable[..., CurrentUser]:
    """要求当前用户必须属于指定角色。

    Args:
        role_code: 目标角色编码

    Returns:
        依赖项函数，校验通过后返回当前用户
    """

    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role_code != role_code and current_user.role_code != SystemRoleCode.SUPERADMIN.mark:
            raise AuthorizationException(message=f"需要角色 {role_code}")
        return current_user

    return dependency


def require_user_permission(permission_code: str) -> Callable[..., CurrentUser]:
    """要求当前用户必须拥有指定权限。权限结果按角色缓存。

    Args:
        permission_code: 目标权限编码

    Returns:
        依赖项函数，校验通过后返回当前用户
    """

    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> CurrentUser:
        if not permission_service.has_permission(current_user.id, permission_code):
            raise AuthorizationException(message=f"缺少权限: {permission_code}")
        return current_user

    return dependency


def get_user_operator_context(current_user: CurrentUser, request: Request | None = None) -> dict[str, object]:
    """构造用户态操作人上下文（供写操作审计/日志使用）。"""
    client_ip = None
    if request:
        client_ip = request.client.host if request.client else None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
    return {
        "operator_id": current_user.id,
        "operator_name": current_user.username,
        "ip_address": client_ip,
    }


def is_admin_user(user: CurrentUser) -> bool:
    """判断当前用户是否为管理员或超管（可查看全部数据）。"""
    return "*" in user.permissions or user.role_code in (
        SystemRoleCode.SUPERADMIN.mark,
        SystemRoleCode.ADMIN.mark,
    )


def get_station_service(
    db_session: Session = Depends(get_db_session),
) -> StationMessageService:
    """创建站内信服务。"""
    from src.repositories.station_message_repository import StationMessageRepository
    from src.services.admin.station_service import StationMessageService

    return StationMessageService(repository=StationMessageRepository(session=db_session))


def get_menu_repository(
    db_session: Session = Depends(get_db_session),
) -> MenuRepository:
    """获取菜单仓库实例。"""
    from src.repositories.menu_repository import MenuRepository

    return MenuRepository(session=db_session)


def get_user_notification_config_repository(
    db_session: Session = Depends(get_db_session),
) -> UserNotificationConfigRepository:
    """获取用户通知渠道配置仓库实例。"""
    from src.repositories.notification_config_repository import UserNotificationConfigRepository

    return UserNotificationConfigRepository(session=db_session)


def get_profile_service(
    user_repository: UserRepository = Depends(get_user_repository),
    menu_repository: MenuRepository = Depends(get_menu_repository),
    config_repository: UserNotificationConfigRepository = Depends(get_user_notification_config_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    station_service: StationMessageService = Depends(get_station_service),
) -> ProfileService:
    """创建个人中心业务服务。"""
    from src.services.admin.profile_service import ProfileService

    return ProfileService(
        user_repository=user_repository,
        menu_repository=menu_repository,
        config_repository=config_repository,
        dispatcher=dispatcher,
        station_service=station_service,
    )


def get_assistant_conversation_repository(
    db_session: Session = Depends(get_db_session),
) -> AssistantConversationRepository:
    """获取 AI 助手会话仓库实例。"""
    from src.repositories.assistant_repository import AssistantConversationRepository

    return AssistantConversationRepository(session=db_session)


def get_assistant_message_repository(
    db_session: Session = Depends(get_db_session),
) -> AssistantMessageRepository:
    """获取 AI 助手消息仓库实例。"""
    from src.repositories.assistant_repository import AssistantMessageRepository

    return AssistantMessageRepository(session=db_session)


def get_assistant_feedback_repository(
    db_session: Session = Depends(get_db_session),
) -> AssistantFeedbackRepository:
    """获取 AI 助手反馈仓库实例。"""
    from src.repositories.assistant_repository import AssistantFeedbackRepository

    return AssistantFeedbackRepository(session=db_session)


def get_assistant_service(
    conversation_repository: AssistantConversationRepository = Depends(get_assistant_conversation_repository),
    message_repository: AssistantMessageRepository = Depends(get_assistant_message_repository),
    feedback_repository: AssistantFeedbackRepository = Depends(get_assistant_feedback_repository),
) -> AssistantService:
    """创建 AI 助手编排服务（LLM / 工具注册表 / 知识库默认懒加载单例）。"""
    from src.services.admin.assistant_service import AssistantService

    return AssistantService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        feedback_repository=feedback_repository,
    )
