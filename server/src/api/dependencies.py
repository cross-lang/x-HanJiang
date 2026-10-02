#!/usr/bin/env python3
"""
FastAPI 依赖注入模块
本模块定义了 API 层通用的 FastAPI Depends 依赖项工厂函数，
用于在路由处理函数中通过参数注入公共依赖。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.constants.constants import (
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_AUTHORIZATION,
    OPENAPI_HEADER_DATE,
)
from src.constants.enums import SystemRoleCode
from src.core.exceptions import AuthorizationException
from src.infras.database import get_db_session
from src.schemas.auth import CurrentUser
from src.schemas.common import PaginatedRequest
from src.schemas.openapi_app import CurrentApp
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.services.file_service import FileStorageService
from src.services.health_service import HealthService
from src.services.notification_service import NotificationService
from src.services.permission_service import PermissionService

if TYPE_CHECKING:
    from src.notification.dispatcher import NotificationDispatcher
    from src.repositories.assistant_repository import (
        AssistantConversationRepository,
        AssistantFeedbackRepository,
        AssistantMessageRepository,
    )
    from src.repositories.login_log_repository import LoginLogRepository
    from src.repositories.menu_repository import MenuRepository
    from src.repositories.notification_preference_repository import NotificationPreferenceRepository
    from src.repositories.notification_recipient_repository import NotificationRecipientRepository
    from src.repositories.permission_repository import PermissionRepository
    from src.repositories.role_permission_repository import RolePermissionRepository
    from src.repositories.role_repository import RoleRepository
    from src.repositories.user_repository import UserRepository
    from src.services.announcement_service import AnnouncementService
    from src.services.assistant_service import AssistantService
    from src.services.dashboard_service import DashboardService
    from src.services.login_log_service import LoginLogService
    from src.services.openapi_app_service import OpenApiAppService
    from src.services.profile_service import ProfileService
    from src.services.role_service import RoleService
    from src.services.search_service import SearchService
    from src.services.station_service import StationMessageService
    from src.services.system_notification_config_service import SystemNotificationConfigService
    from src.services.system_notification_service import SystemNotificationService
    from src.services.user_service import UserService

# HTTP Bearer 认证方案（auto_error=False，缺失令牌时由 get_current_user 统一抛 401）
_bearer_scheme = HTTPBearer(auto_error=False)

# 开放平台 API Key 认证方案（Swagger UI 右上角会出现 Authorize 按钮）
_app_id_scheme = APIKeyHeader(name=OPENAPI_HEADER_APP_ID, scheme_name="OpenAppId", auto_error=False)

_app_key_scheme = APIKeyHeader(name=OPENAPI_HEADER_APP_KEY, scheme_name="OpenAppKey", auto_error=False)

_app_date_scheme = APIKeyHeader(name=OPENAPI_HEADER_DATE, scheme_name="OpenAppDate", auto_error=False)

_app_auth_scheme = APIKeyHeader(name=OPENAPI_HEADER_AUTHORIZATION, scheme_name="OpenAppAuthorization", auto_error=False)


def get_request_id(request: Request) -> str | None:
    """从请求状态中获取当前请求 ID。"""
    return getattr(request.state, "request_id", None)


def get_pagination(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedRequest:
    """获取分页参数。"""
    return PaginatedRequest(page=page, page_size=page_size)


def get_notification_dispatcher(
    db_session: Session = Depends(get_db_session),
) -> NotificationDispatcher:
    """获取通知调度器实例（供 AlertService 等内部服务使用）。"""
    from src.infras.notification import get_registry
    from src.notification.dispatcher import NotificationDispatcher

    return NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )


def get_notification_service(
    db_session: Session = Depends(get_db_session),
) -> NotificationService:
    """获取通知业务服务实例。"""
    from src.infras.notification import get_registry
    from src.notification.dispatcher import NotificationDispatcher
    from src.repositories.notification_repository import NotificationRepository

    dispatcher = NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )
    return NotificationService(
        dispatcher=dispatcher,
        repository=NotificationRepository(session=db_session),
    )


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


def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> UserService:
    """使用当前请求的 Repository 创建用户服务。"""
    from src.services.user_service import UserService

    return UserService(
        user_repository=user_repository,
        role_repository=role_repository,
        dispatcher=dispatcher,
    )


def get_alert_service(
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    db_session: Session = Depends(get_db_session),
) -> AlertService:
    """获取告警服务实例。"""
    return AlertService(dispatcher=dispatcher, session=db_session)


def get_health_service() -> HealthService:
    """获取健康检查服务（下游探测与告警编排在 service 层）。"""
    from src.services.health_service import HealthService

    return HealthService()


def get_announcement_service(
    db_session: Session = Depends(get_db_session),
) -> AnnouncementService:
    """获取公告业务服务实例。"""
    from src.repositories.announcement_repository import AnnouncementRepository
    from src.services.announcement_service import AnnouncementService

    return AnnouncementService(repository=AnnouncementRepository(session=db_session))


def get_system_notification_service(
    db_session: Session = Depends(get_db_session),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> SystemNotificationService:
    """获取系统通知（广播）业务服务实例。"""
    from src.repositories.station_message_repository import StationMessageRepository
    from src.repositories.system_notification_repository import SystemNotificationRepository
    from src.repositories.user_repository import UserRepository
    from src.services.station_service import StationMessageService
    from src.services.system_notification_service import SystemNotificationService

    return SystemNotificationService(
        notice_repository=SystemNotificationRepository(session=db_session),
        user_repository=UserRepository(session=db_session),
        station_service=StationMessageService(repository=StationMessageRepository(session=db_session)),
        dispatcher=dispatcher,
    )


def get_audit_service(
    db_session: Session = Depends(get_db_session),
) -> AuditService:
    """获取审计服务。"""
    from src.repositories.audit_log_repository import AuditLogRepository

    return AuditService(audit_log_repository=AuditLogRepository(session=db_session))


def get_file_service(
    db_session: Session = Depends(get_db_session),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> FileStorageService:
    """获取文件存储服务，使用 StorageProvider 抽象层 + 请求级仓库。"""
    from src.infras.storage import get_cached_storage_provider
    from src.repositories.file_repository import FileRepository

    return FileStorageService(
        file_repository=FileRepository(session=db_session),
        provider=get_cached_storage_provider(),
        dispatcher=dispatcher,
    )


def get_dashboard_service(
    db_session: Session = Depends(get_db_session),
) -> DashboardService:
    """获取仪表盘统计服务。"""
    from src.repositories.dashboard_repository import DashboardRepository
    from src.services.dashboard_service import DashboardService

    return DashboardService(repository=DashboardRepository(session=db_session))


def get_system_notification_config_service(
    db_session: Session = Depends(get_db_session),
) -> SystemNotificationConfigService:
    """获取系统通知配置服务。"""
    from src.repositories.system_notification_config_repository import (
        SystemNotificationConfigRepository,
    )
    from src.services.system_notification_config_service import SystemNotificationConfigService

    return SystemNotificationConfigService(repository=SystemNotificationConfigRepository(session=db_session))


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


def get_role_service(
    role_repository: RoleRepository = Depends(get_role_repository),
    role_permission_repository: RolePermissionRepository = Depends(get_role_permission_repository),
    permission_repository: PermissionRepository = Depends(get_permission_repository),
) -> RoleService:
    """使用当前请求的 Repository 创建角色服务。"""
    from src.services.role_service import RoleService

    return RoleService(
        role_repository=role_repository,
        role_permission_repository=role_permission_repository,
        permission_repository=permission_repository,
    )


def get_permission_service(
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    role_permission_repository: RolePermissionRepository = Depends(get_role_permission_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> PermissionService:
    """使用当前请求的 Repository 创建权限服务。"""
    from src.services.permission_service import PermissionService

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
    from src.services.login_log_service import LoginLogService

    return LoginLogService(
        login_log_repository=login_log_repository,
        user_repository=user_repository,
    )


def get_openapi_app_service(
    db_session: Session = Depends(get_db_session),
) -> OpenApiAppService:
    """创建开放平台应用管理服务。"""
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.openapi_app_service import OpenApiAppService

    return OpenApiAppService(repo=OpenApiAppRepository(session=db_session))


def get_search_service(
    db_session: Session = Depends(get_db_session),
) -> SearchService:
    """获取搜索服务。"""
    from src.repositories.search_repository import SearchRepository
    from src.services.search_service import SearchService

    return SearchService(repository=SearchRepository(session=db_session))


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


# ============================================================

# 面向应用（开放平台）鉴权

# ============================================================


def get_app_operator_context(app: CurrentApp) -> dict[str, object]:
    """构造应用态操作人上下文（供写操作审计/日志使用）。"""
    return {
        "operator_id": app.app_id,
        "operator_name": app.name,
    }


async def get_current_app(
    request: Request,
    _app_id: str | None = Depends(_app_id_scheme),
    _app_key: str | None = Depends(_app_key_scheme),
    _app_date: str | None = Depends(_app_date_scheme),
    _app_auth: str | None = Depends(_app_auth_scheme),
    service: OpenApiAppService = Depends(get_openapi_app_service),
) -> CurrentApp:
    """解析开放平台应用身份，委托给 OpenApiAppService。"""
    current = await service.authenticate(request)
    request.state.current_app = current
    return current


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
    from src.services.station_service import StationMessageService

    return StationMessageService(repository=StationMessageRepository(session=db_session))


def get_menu_repository(
    db_session: Session = Depends(get_db_session),
) -> MenuRepository:
    """获取菜单仓库实例。"""
    from src.repositories.menu_repository import MenuRepository

    return MenuRepository(session=db_session)


def get_notification_preference_repository(
    db_session: Session = Depends(get_db_session),
) -> NotificationPreferenceRepository:
    """获取通知偏好仓库实例。"""
    from src.repositories.notification_preference_repository import NotificationPreferenceRepository

    return NotificationPreferenceRepository(session=db_session)


def get_notification_recipient_repository(
    db_session: Session = Depends(get_db_session),
) -> NotificationRecipientRepository:
    """获取通知接收人仓库实例。"""
    from src.repositories.notification_recipient_repository import NotificationRecipientRepository

    return NotificationRecipientRepository(session=db_session)


def get_profile_service(
    user_repository: UserRepository = Depends(get_user_repository),
    menu_repository: MenuRepository = Depends(get_menu_repository),
    preference_repository: NotificationPreferenceRepository = Depends(get_notification_preference_repository),
    recipient_repository: NotificationRecipientRepository = Depends(get_notification_recipient_repository),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
    station_service: StationMessageService = Depends(get_station_service),
) -> ProfileService:
    """创建个人中心业务服务。"""
    from src.services.profile_service import ProfileService

    return ProfileService(
        user_repository=user_repository,
        menu_repository=menu_repository,
        preference_repository=preference_repository,
        recipient_repository=recipient_repository,
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
    from src.services.assistant_service import AssistantService

    return AssistantService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        feedback_repository=feedback_repository,
    )


def require_app_scope(scope: str) -> Callable[..., CurrentApp]:
    """要求当前应用必须拥有指定 scope。

    Args:
        scope: 目标 scope 编码

    Returns:
        依赖项函数，校验通过后返回当前应用
    """

    def dependency(app: CurrentApp = Depends(get_current_app)) -> CurrentApp:
        if scope not in app.scopes:
            raise AuthorizationException(message=f"应用缺少 scope: {scope}")
        return app

    return dependency
