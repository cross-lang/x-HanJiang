#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件模块

本模块提供 HTTP 请求处理中间件，包括：
    - RequestIDMiddleware：为每个请求生成唯一 ID 并注入到请求状态和响应头
    - RequestLoggingMiddleware：全链路请求记录（路径、入参、响应耗时、客户端IP、操作人ID）
    - ExceptionHandlingMiddleware：统一异常处理（404、405、500、限流、权限异常）
    - RateLimitMiddleware：请求限流（基于 slowapi）
    - AuthMiddleware：认证中间件基础封装

Usage:
    from src.core.middleware import RequestIDMiddleware, RequestLoggingMiddleware

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
"""

import datetime
import json
import time
import uuid
from typing import Any, Callable, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.constants import REQUEST_ID_HEADER
from src.core.config import settings
from src.core.logger import logger


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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件。

    全链路请求记录，包括：路径、入参、响应耗时、客户端IP、操作人ID。
    在请求开始和结束时打印日志，便于追踪和性能分析。

    Attributes:
        app: ASGI 应用实例
    """

    def __init__(self, app: ASGIApp) -> None:
        """初始化请求日志记录中间件。

        Args:
            app: ASGI 应用实例
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求，记录请求日志。

        Args:
            request: 当前 HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应
        """
        start_time: float = time.time()
        request_id: str = getattr(request.state, "request_id", "-")
        client_ip: str = self._get_client_ip(request)

        logger.bind(request_id=request_id).info(
            f"Request started: {request.method} {request.url.path} "
            f"from {client_ip} headers={dict(request.headers)}"
        )

        try:
            body: dict[str, Any] = await self._get_request_body(request)
            if body:
                logger.bind(request_id=request_id).debug(f"Request body: {body}")
        except Exception:
            pass

        response: Response = await call_next(request)

        elapsed: float = (time.time() - start_time) * 1000
        logger.bind(request_id=request_id).info(
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={elapsed:.2f}ms"
        )

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """从请求中提取客户端真实 IP 地址。

        Args:
            request: FastAPI 请求对象

        Returns:
            str: 客户端 IP 地址
        """
        forwarded: Optional[str] = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip: Optional[str] = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host

        return "unknown"

    @staticmethod
    async def _get_request_body(request: Request) -> dict[str, Any]:
        """获取请求体内容。

        Args:
            request: FastAPI 请求对象

        Returns:
            dict[str, Any]: 请求体字典
        """
        try:
            body = await request.json()
            return body if isinstance(body, dict) else {}
        except Exception:
            return {}


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件。

    全局统一拦截404、405、500、限流、权限异常，全部封装为标准错误返回格式，
    不向前端暴露原生服务报错堆栈。

    Attributes:
        app: ASGI 应用实例
    """

    def __init__(self, app: ASGIApp) -> None:
        """初始化异常处理中间件。

        Args:
            app: ASGI 应用实例
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求，统一捕获异常。

        Args:
            request: 当前 HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应（标准化错误响应）
        """
        try:
            return await call_next(request)
        except HTTPException as exc:
            request_id: str = getattr(request.state, "request_id", "-")
            logger.bind(request_id=request_id).warning(
                f"HTTP exception: {exc.status_code} {exc.detail}"
            )
            return self._create_error_response(
                status_code=exc.status_code,
                message=str(exc.detail),
                request_id=request_id,
            )
        except Exception as exc:
            request_id: str = getattr(request.state, "request_id", "-")
            logger.bind(request_id=request_id).exception(
                f"Unhandled exception: {exc}"
            )
            return self._create_error_response(
                status_code=500,
                message="Internal server error",
                request_id=request_id,
            )

    @staticmethod
    def _create_error_response(
        status_code: int,
        message: str,
        request_id: str,
    ) -> Response:
        """创建标准化错误响应。

        Args:
            status_code: HTTP 状态码
            message: 错误消息
            request_id: 请求追踪 ID

        Returns:
            Response: 标准化错误响应
        """
        response_data: dict[str, Any] = {
            "code": status_code,
            "message": message,
            "data": None,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "request_id": request_id,
        }

        return Response(
            content=json.dumps(response_data),
            status_code=status_code,
            media_type="application/json",
        )


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

    limiter: Limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit.per_minute}/minute"],
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
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        authorization: Optional[str] = request.headers.get("Authorization")
        if not authorization:
            from src.core.exceptions import AuthenticationException

            raise AuthenticationException("Missing Authorization header")

        return await call_next(request)