#!/usr/bin/env python3
"""
登录日志业务逻辑实现

提供登录日志查询能力（登录日志为只读流水，不支持创建/更新/删除的对外接口）。

Classes:
    LoginLogService: 登录日志业务逻辑实现
"""

from datetime import datetime
from typing import Any

from src.models.entities.log_entity import LoginLogEntity
from src.repositories.login_log_repository import LoginLogRepository
from src.schemas.login_log import LoginLogResponse
from src.services.base_service import BaseService


class LoginLogService(BaseService[LoginLogResponse, int]):
    """登录日志业务逻辑实现。"""

    def __init__(self, login_log_repository: LoginLogRepository) -> None:
        """初始化登录日志服务。"""
        self._repository: LoginLogRepository = login_log_repository

    def get_by_id(self, id: int) -> LoginLogResponse | None:
        """根据日志 ID 查询登录日志。"""
        entity = self._repository.get_by_id(id)
        return self._to_response(entity) if entity else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """查询全部登录日志（分页，按时间倒序）。"""
        skip = (page - 1) * page_size
        entities = self._repository.get_all(skip=skip, limit=page_size)
        return {
            "items": [self._to_response(e) for e in entities],
            "total": self._repository.count_all(),
            "page": page,
            "page_size": page_size,
        }

    def search(
        self,
        user_id: int | None = None,
        status: str | None = None,
        login_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """按条件搜索登录日志（分页，按时间倒序）。"""
        skip = (page - 1) * page_size
        entities, total = self._repository.search(
            user_id=user_id,
            status=status,
            login_type=login_type,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._to_response(e) for e in entities],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _to_response(self, entity: LoginLogEntity) -> LoginLogResponse:
        """实体转响应 DTO。"""
        return LoginLogResponse(
            id=entity.id,
            user_id=entity.user_id,
            login_type=entity.login_type,
            ip_address=entity.ip_address,
            status=entity.status,
            created_at=entity.created_at,
        )
