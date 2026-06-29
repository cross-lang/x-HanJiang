#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件模块

本模块提供 HTTP 请求处理中间件，包括：
    - RequestIDMiddleware：为每个请求生成唯一 ID 并注入到请求状态和响应头
    - 请求限流配置（基于 slowapi）
    - 认证中间件基础封装

Usage:
    from src.core.middleware import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)
"""

import uuid
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.common.constants import REQUEST_ID_HEADER


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件。

    为每个 HTTP 请求生成唯一的 UUID，存储在 request.state.request_id 中，
    并在响应头中添加 X-Request-ID 字段。该 ID 贯穿整个请求生命周期，
    用于日志追踪和问题排查。

    Attributes:
        app: ASGI 应用实例
    """

    def __init__(self, app: ASGIApp) -> None:
        """初始化请求 ID 中间件。

        Args:
            app: ASGI 应用实例
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求，生成并注入请求 ID。

        Args:
            request: 当前 HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应，包含 X-Request-ID 头
        """
        request_id: str = str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id

        return response


def setup_rate_limiter(app: FastAPI) -> Any:
    """配置请求限流器。

    基于 slowapi 实现，限制每个 IP 每分钟的请求次数。
    从 Settings 中读取限流配置。

    Args:
        app: FastAPI 应用实例

    Returns:
        Limiter: slowapi 限流器实例
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from src.core.config import settings

    limiter: Limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit.RATE_LIMIT_PER_MINUTE}/minute"],
    )

    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return limiter


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件基础封装。

    提供请求认证的基础框架，验证 Authorization 请求头。
    可配置跳过路径列表（如健康检查、文档等）。

    此中间件为骨架实现，可根据实际需求扩展 JWT/OAuth 等认证逻辑。

    Attributes:
        skip_paths: 不需要认证的路径列表
    """

    def __init__(
        self,
        app: ASGIApp,
        skip_paths: Optional[list[str]] = None,
    ) -> None:
        """初始化认证中间件。

        Args:
            app: ASGI 应用实例
            skip_paths: 不需要认证的路径前缀列表
        """
        super().__init__(app)
        self.skip_paths: list[str] = skip_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/version",
        ]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求认证。

        检查请求路径是否在跳过列表中，否则验证 Authorization 头。

        Args:
            request: 当前 HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应

        Raises:
            AuthenticationException: 认证失败时抛出
        """
        # 跳过不需要认证的路径
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        # 检查 Authorization 头
        authorization: Optional[str] = request.headers.get("Authorization")
        if not authorization:
            from src.core.exceptions import AuthenticationException

            raise AuthenticationException("Missing Authorization header")

        # 骨架：此处可扩展实际的 JWT/OAuth 验证逻辑
        # token: str = authorization.replace("Bearer ", "")
        # payload: dict = decode_jwt(token)

        return await call_next(request)
