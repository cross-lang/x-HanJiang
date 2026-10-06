"""全局搜索服务 — 组合各实体搜索结果。
服务层不接触数据库会话、不编写 SQL，
仅通过仓库获取实体数据，再负责结果组装。
"""

from typing import Any

from src.models.entities.announcement_entity import AnnouncementEntity
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.file_entity import FileEntity
from src.models.entities.system_notification_entity import SystemNotificationEntity
from src.models.entities.user_entity import PermissionEntity, RoleEntity, UserEntity
from src.repositories.search_repository import SearchRepository

# 支持搜索的实体分类（与仓库方法一一对应）
SEARCHABLE_CATEGORIES: tuple[str, ...] = (
    "users",
    "roles",
    "permissions",
    "apps",
    "files",
    "notices",
    "announcements",
)


class SearchService:
    """搜索服务。"""

    def __init__(self, repository: SearchRepository) -> None:
        self._repository = repository

    def search(
        self,
        keyword: str,
        limit: int,
        categories: list[str] | tuple[str, ...] = SEARCHABLE_CATEGORIES,
    ) -> dict[str, list[dict[str, Any]]]:
        """按分类返回各实体前 N 条搜索结果。"""
        result: dict[str, list[dict[str, Any]]] = {}
        if "users" in categories:
            result["users"] = [self._to_user(r) for r in self._repository.search_users(keyword, limit)]
        if "roles" in categories:
            result["roles"] = [self._to_role(r) for r in self._repository.search_roles(keyword, limit)]
        if "permissions" in categories:
            result["permissions"] = [
                self._to_permission(r) for r in self._repository.search_permissions(keyword, limit)
            ]
        if "apps" in categories:
            result["apps"] = [self._to_app(r) for r in self._repository.search_apps(keyword, limit)]
        if "files" in categories:
            result["files"] = [self._to_file(r) for r in self._repository.search_files(keyword, limit)]
        if "notices" in categories:
            result["notices"] = [self._to_notice(r) for r in self._repository.search_notices(keyword, limit)]
        if "announcements" in categories:
            result["announcements"] = [
                self._to_announcement(r) for r in self._repository.search_announcements(keyword, limit)
            ]
        return result

    @staticmethod
    def _to_user(r: UserEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "username": r.username,
            "name": r.name,
            "email": r.email,
            "status": r.status,
        }

    @staticmethod
    def _to_role(r: RoleEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "role_name": r.role_name,
            "role_code": r.role_code,
            "role_type": r.role_type,
            "status": r.status,
        }

    @staticmethod
    def _to_permission(r: PermissionEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "perm_code": r.perm_code,
            "perm_name": r.perm_name,
            "module": r.module,
        }

    @staticmethod
    def _to_app(r: OpenApiAppEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "app_id": r.app_id,
            "name": r.name,
            "status": r.status,
        }

    @staticmethod
    def _to_file(r: FileEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "original_name": r.original_name,
            "folder": r.folder,
            "extension": r.extension,
        }

    @staticmethod
    def _to_notice(r: SystemNotificationEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "title": r.title,
            "notice_type": r.notice_type,
            "status": r.status,
        }

    @staticmethod
    def _to_announcement(r: AnnouncementEntity) -> dict[str, Any]:
        return {
            "id": r.id,
            "title": r.title,
            "position": r.position,
            "status": r.status,
        }
