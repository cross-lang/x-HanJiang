"""数据库实体模型包。"""

from src.models.entities.app_entity import OpenApiAppEntity, OpenApiScopeEntity
from src.models.entities.audit_entity import AuditLogEntity
from src.models.entities.file_entity import FileEntity
from src.models.entities.log_entity import LoginLogEntity
from src.models.entities.menu_entity import MenuEntity
from src.models.entities.notification_recipient_entity import (
    NotificationRecipientEntity,
)
from src.models.entities.notification_preference_entity import (
    UserNotificationPreferenceEntity,
)
from src.models.entities.notification_entity import NotificationRecordEntity
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
    UserEntity,
    UserRoleEntity,
)

__all__ = [
    "UserEntity",
    "RoleEntity",
    "PermissionEntity",
    "RolePermissionEntity",
    "UserRoleEntity",
    "LoginLogEntity",
    "AuditLogEntity",
    "NotificationRecordEntity",
    "NotificationRecipientEntity",
    "UserNotificationPreferenceEntity",
    "OpenApiAppEntity",
    "OpenApiScopeEntity",
    "FileEntity",
    "MenuEntity",
]
