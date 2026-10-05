#!/usr/bin/env python3
"""
开放平台门户域（/api/open-portal/v1）FastAPI 依赖注入模块。

本文件承载开放平台门户（开发者账号体系，与管理系统用户隔离）域的全部依赖：
- 开发者认证服务与当前登录开发者解析（get_current_developer）
- 开发者资料 / 应用管理 / 站内信服务工厂

跨域公共依赖（get_db_session / _bearer_scheme 等）位于 src/api/dependencies.py；
管理端域见 src/api/admin/dependencies.py；开放接口域见 src/api/open/dependencies.py。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.api.dependencies import _bearer_scheme, get_db_session
from src.schemas.open_portal.auth import CurrentDeveloper

if TYPE_CHECKING:
    from src.repositories.developer_repository import DeveloperRepository
    from src.services.open_portal.app_service import DeveloperOpenAppService
    from src.services.open_portal.auth_service import DeveloperAuthService
    from src.services.open_portal.developer_message_service import DeveloperMessageService
    from src.services.open_portal.developer_service import DeveloperService


def get_developer_message_service(
    db_session: Session = Depends(get_db_session),
) -> DeveloperMessageService:
    """创建开发者站内信服务（开放平台门户域，developer_messages 表）。"""
    from src.repositories.developer_message_repository import DeveloperMessageRepository
    from src.services.open_portal.developer_message_service import DeveloperMessageService

    return DeveloperMessageService(repository=DeveloperMessageRepository(session=db_session))


def get_developer_repository(
    db_session: Session = Depends(get_db_session),
) -> DeveloperRepository:
    """获取开发者仓库实例。"""
    from src.repositories.developer_repository import DeveloperRepository

    return DeveloperRepository(session=db_session)


def get_developer_auth_service(
    developer_repository: DeveloperRepository = Depends(get_developer_repository),
) -> DeveloperAuthService:
    """获取开发者认证服务（门户域）。"""
    from src.services.open_portal.auth_service import DeveloperAuthService

    return DeveloperAuthService(repository=developer_repository)


def get_developer_service(
    developer_repository: DeveloperRepository = Depends(get_developer_repository),
) -> DeveloperService:
    """获取开发者资料服务（门户域）。"""
    from src.services.open_portal.developer_service import DeveloperService

    return DeveloperService(repository=developer_repository)


def get_developer_open_app_service(
    db_session: Session = Depends(get_db_session),
) -> DeveloperOpenAppService:
    """获取开发者应用管理服务（门户域）。"""
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.open_portal.app_service import DeveloperOpenAppService

    return DeveloperOpenAppService(repo=OpenApiAppRepository(session=db_session))


def get_current_developer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: DeveloperAuthService = Depends(get_developer_auth_service),
) -> CurrentDeveloper:
    """解析 Bearer 令牌，返回当前登录开发者（门户 JWT，与管理系统用户隔离）。"""
    token = credentials.credentials if credentials is not None else None
    return auth_service.get_current_developer(token)
