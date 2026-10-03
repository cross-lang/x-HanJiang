#!/usr/bin/env python3
"""开放平台开发者资料与认证接口（门户 JWT）。
路由前缀：/api/open-portal/v1/developer
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_current_developer,
    get_developer_service,
)
from src.api.response import success_response
from src.schemas.open.auth import (
    CurrentDeveloper,
    DeveloperCertificationRequest,
    DeveloperProfileUpdateRequest,
)
from src.services.open_portal.developer_service import DeveloperService

router = APIRouter(prefix="/developer", tags=["开放平台：开发者资料"])


@router.get(
    "/profile",
    summary="开发者资料",
    description="当前登录开发者的个人资料（含认证类型与认证状态）",
)
def get_profile(
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperService = Depends(get_developer_service),
) -> JSONResponse:
    return success_response(service.get_profile(current_developer.id).model_dump(), request)


@router.put(
    "/profile",
    summary="更新开发者资料",
    description="更新姓名/手机号",
)
def update_profile(
    body: DeveloperProfileUpdateRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperService = Depends(get_developer_service),
) -> JSONResponse:
    return success_response(service.update_profile(current_developer.id, body).model_dump(), request)


@router.post(
    "/certification",
    summary="提交开发者认证申请",
    description="预留能力：个人/企业认证申请，提交后认证状态置 pending，等待管理员审批",
)
def apply_certification(
    body: DeveloperCertificationRequest,
    request: Request,
    current_developer: CurrentDeveloper = Depends(get_current_developer),
    service: DeveloperService = Depends(get_developer_service),
) -> JSONResponse:
    return success_response(service.apply_certification(current_developer.id, body).model_dump(), request)
