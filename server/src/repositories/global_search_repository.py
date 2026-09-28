"""全局搜索仓库 — 跨实体关键字搜索的数据访问层。
仅负责数据查询（依赖实体模型），不做业务判断；
权限过滤与结果组装由服务层/接口层负责。
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.file_entity import FileEntity
from src.models.entities.user_entity import PermissionEntity, RoleEntity, UserEntity


class GlobalSearchRepository:
    """全局搜索仓库。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search_users(self, keyword: str, limit: int) -> list[UserEntity]:
        like = f"%{keyword}%"
        return (
            self._session.query(UserEntity)
            .filter(
                or_(
                    UserEntity.username.like(like),
                    UserEntity.name.like(like),
                    UserEntity.email.like(like),
                )
            )
            .filter(UserEntity.deleted_at.is_(None))
            .limit(limit)
            .all()
        )

    def search_roles(self, keyword: str, limit: int) -> list[RoleEntity]:
        like = f"%{keyword}%"
        return (
            self._session.query(RoleEntity)
            .filter(
                or_(
                    RoleEntity.role_name.like(like),
                    RoleEntity.role_code.like(like),
                )
            )
            .filter(RoleEntity.deleted_at.is_(None))
            .limit(limit)
            .all()
        )

    def search_permissions(self, keyword: str, limit: int) -> list[PermissionEntity]:
        like = f"%{keyword}%"
        return (
            self._session.query(PermissionEntity)
            .filter(
                or_(
                    PermissionEntity.perm_code.like(like),
                    PermissionEntity.perm_name.like(like),
                )
            )
            .limit(limit)
            .all()
        )

    def search_apps(self, keyword: str, limit: int) -> list[OpenApiAppEntity]:
        like = f"%{keyword}%"
        return (
            self._session.query(OpenApiAppEntity)
            .filter(
                or_(
                    OpenApiAppEntity.name.like(like),
                    OpenApiAppEntity.app_id.like(like),
                )
            )
            .filter(OpenApiAppEntity.deleted_at.is_(None))
            .limit(limit)
            .all()
        )

    def search_files(self, keyword: str, limit: int) -> list[FileEntity]:
        like = f"%{keyword}%"
        return (
            self._session.query(FileEntity)
            .filter(
                or_(
                    FileEntity.original_name.like(like),
                    FileEntity.file_key.like(like),
                )
            )
            .filter(FileEntity.is_deleted.is_(False))
            .limit(limit)
            .all()
        )
