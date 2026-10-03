#!/usr/bin/env python3
"""开放平台 scope 目录接口（门户 JWT，供开发者建应用/申请权限时勾选）。
路由前缀：/api/open-portal/v1/scopes
说明：scope 元数据唯一来源为 constants/scopes.py 启动时对账的 openapi_scopes 表，
与管理端 /api/v1/admin/apps/scopes 数据一致（共享 repository 与公共映射函数），
入口归属开发者门户域，不反向依赖管理端服务。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_developer, get_db_session
from src.api.response import success_response
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.open.auth import CurrentDeveloper
from src.utils.openapi_utils import build_scope_dict_list

router = APIRouter(prefix="/scopes", tags=["开放平台：scope 目录"])


@router.get(
    "",
    summary="scope 目录",
    description="全部可用（未废弃）的开放平台 scope，按模块分组展示",
)
def list_scopes(
    request: Request,
    _current_developer: CurrentDeveloper = Depends(get_current_developer),
    db_session: Session = Depends(get_db_session),
) -> JSONResponse:
    entities = OpenApiAppRepository(session=db_session).list_active_scopes()
    return success_response(build_scope_dict_list(entities), request)
