#!/usr/bin/env python3
"""
登录日志接口

提供登录日志查询的 RESTful API 端点（只读流水）。

Endpoints:
    GET /login-logs:        登录日志列表（分页/过滤）
    GET /login-logs/{id}:   登录日志详情
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import get_current_user, get_login_log_service
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.schemas.common import PaginatedResponse
from src.schemas.login_log import LoginLogResponse
from src.services.login_log_service import LoginLogService

router = APIRouter(prefix="/login-logs", tags=["login-logs"])


@router.get(
    "",
    summary="登录日志列表",
    description="查询登录日志列表（分页，支持用户/结果/方式/时间范围过滤）",
)
async def list_login_logs(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    status: str | None = None,
    login_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    service: LoginLogService = Depends(get_login_log_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """登录日志列表接口。"""
    result = service.search(
        user_id=user_id,
        status=status,
        login_type=login_type,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[LoginLogResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"]
            if result["page_size"] > 0
            else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/{log_id}",
    summary="登录日志详情",
    description="根据 ID 查询登录日志详情",
)
async def get_login_log(
    log_id: int,
    request: Request,
    service: LoginLogService = Depends(get_login_log_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """查询单条登录日志接口。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(log_id)
    if result is None:
        raise NotFoundException(message=f"登录日志 {log_id} 不存在")
    return success_response(result.model_dump(), request)
