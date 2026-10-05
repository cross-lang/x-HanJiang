#!/usr/bin/env python3
"""
开放接口域（/api/open/v1）FastAPI 依赖注入模块。

本文件承载开放接口（机器身份 AppId/Key 签名）域的全部依赖：
- AppKey 明文 / HanJiang-1 签名所需请求头解析方案（_app_*_scheme）
- 网关鉴权（get_current_app）与 scope 门槛（require_app_scope）
- 应用态操作人上下文（get_app_operator_context）

开放能力复用管理系统业务服务（用户/角色/文件），
get_user_service / get_role_service / get_file_service 在此转发自管理端依赖模块。
跨域公共依赖见 src/api/dependencies.py；门户域见 src/api/open_portal/dependencies.py。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from src.constants.constants import (
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_AUTHORIZATION,
    OPENAPI_HEADER_DATE,
)
from src.core.exceptions import AuthorizationException
from src.schemas.open.app import CurrentApp
from src.schemas.open.request_context import OpenApiAuthContext
from src.infras.database import get_db_session

# 开放能力封装的管理系统服务（复用 admin 域工厂，保持开放接口调用方单一 import 源）
from src.api.admin.dependencies import get_file_service, get_role_service, get_user_service

if TYPE_CHECKING:
    from src.services.open.gateway_service import OpenGatewayService

# 开放平台 API Key 认证方案（Swagger UI 右上角会出现 Authorize 按钮）
_app_id_scheme = APIKeyHeader(name=OPENAPI_HEADER_APP_ID, scheme_name="OpenAppId", auto_error=False)

_app_key_scheme = APIKeyHeader(name=OPENAPI_HEADER_APP_KEY, scheme_name="OpenAppKey", auto_error=False)

_app_date_scheme = APIKeyHeader(name=OPENAPI_HEADER_DATE, scheme_name="OpenAppDate", auto_error=False)

_app_auth_scheme = APIKeyHeader(name=OPENAPI_HEADER_AUTHORIZATION, scheme_name="OpenAppAuthorization", auto_error=False)


def get_open_gateway_service(
    db_session: Session = Depends(get_db_session),
) -> OpenGatewayService:
    """创建开放接口网关鉴权服务（/api/open/v1，AppId/Key 签名 + 审批门槛）。"""
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.open.gateway_service import OpenGatewayService

    return OpenGatewayService(repo=OpenApiAppRepository(session=db_session))


def get_app_operator_context(app: CurrentApp) -> dict[str, object]:
    """构造应用态操作人上下文（供写操作审计/日志使用）。"""
    return {
        "operator_id": app.app_id,
        "operator_name": app.name,
    }


def _extract_uri(request: Request) -> str:
    """从请求中提取 URI（path + raw query，不含域名）。"""
    uri = request.url.path
    if request.url.query:
        uri += f"?{request.url.query}"
    return uri


async def get_current_app(
    request: Request,
    _app_id: str | None = Depends(_app_id_scheme),
    _app_key: str | None = Depends(_app_key_scheme),
    _app_date: str | None = Depends(_app_date_scheme),
    _app_auth: str | None = Depends(_app_auth_scheme),
    service: OpenGatewayService = Depends(get_open_gateway_service),
) -> CurrentApp:
    """解析开放平台应用身份，委托给开放接口网关鉴权服务（OpenGatewayService）。

    在 API 层把 FastAPI Request 剥离为 OpenApiAuthContext 纯数据后传入，
    services 层不依赖 Web 框架对象（starlette Request / body 流）。
    """
    body = b""
    try:
        body = await request.body()
    except Exception:
        body = b""
    ctx = OpenApiAuthContext(
        app_id=_app_id or "",
        plain_key=_app_key,
        authorization=_app_auth,
        date=_app_date,
        method=request.method,
        uri=_extract_uri(request),
        body=body,
    )
    current = await service.authenticate(ctx)
    request.state.current_app = current
    return current


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
