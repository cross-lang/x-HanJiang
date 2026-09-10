#!/usr/bin/env python3
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
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.constants import REQUEST_ID_HEADER
from src.core.config import settings
from src.core.logger import logger
from src.utils.helpers import mask_sensitive

# 敏感请求头黑名单，日志中始终脱敏
_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-csrftoken",
    }
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件。

    为每个 HTTP 请求生成唯一的 UUID，存储在 request.state.request_id 中，
    并在响应头中添加 X-Request-ID 字段。该 ID 贯穿整个请求生命周期，
    用于日志追踪和问题排查。

    Attributes:
        app: ASGI 应用实例
    """

    def __init__(self, app: ASGIApp, header_name: str = REQUEST_ID_HEADER) -> None:
        super().__init__(app)
        self.header_name: str = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求，生成并注入请求 ID。

        如果请求中已经携带同名头（如上游网关传入），则复用之；
        否则生成新的 UUID。

        Args:
            request: 当前 HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应，包含 X-Request-ID 头
        """
        request_id: str | None = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件。

    全链路请求记录，包括：路径、入参、响应耗时、客户端IP。
    入参日志默认仅在 DEBUG 级别输出，且对敏感字段自动脱敏。
    不消费请求体流，下游 endpoint 可正常解析 body。
    """

    def __init__(self, app: ASGIApp) -> None:
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

        # 记录完整 URL（含 query string）与 query 参数
        full_url: str = str(request.url)
        query_params: dict[str, str] = dict(request.query_params)

        # 过滤敏感请求头后记录
        safe_headers = self._mask_headers(dict(request.headers))
        logger.bind(request_id=request_id).info(
            f"Request started: {request.method} {full_url} "
            f"from {client_ip} query={query_params} headers={safe_headers}"
        )

        if logger.level("DEBUG").no <= 10:  # level no <= DEBUG
            body_preview = await self._safe_read_body(request)
            if body_preview is not None:
                logger.bind(request_id=request_id).debug(
                    f"Request body: {mask_sensitive(body_preview)}"
                )

        response: Response = await call_next(request)

        elapsed: float = (time.time() - start_time) * 1000
        logger.bind(request_id=request_id).info(
            f"Request completed: {request.method} {full_url} "
            f"status={response.status_code} duration={elapsed:.2f}ms"
        )

        return response

    @staticmethod
    def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
        """对敏感请求头进行脱敏。"""
        masked: dict[str, str] = {}
        for k, v in headers.items():
            if k.lower() in _SENSITIVE_HEADERS:
                masked[k] = "****"
            else:
                masked[k] = v
        return masked

    @staticmethod
    async def _safe_read_body(request: Request) -> dict[str, Any] | None:
        """尝试读取请求体用于 DEBUG 日志，不影响下游解析。

        通过缓存到 request._body 让下游仍可重复读取。
        仅在 Content-Type 为 application/json 且请求方法可能含 body 时尝试。

        Args:
            request: 当前 HTTP 请求

        Returns:
            Optional[dict[str, Any]]: 解析后的请求体字典，无法读取时返回 None
        """
        if request.method not in {"POST", "PUT", "PATCH"}:
            return None

        content_type: str = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return None

        try:
            body_bytes = await request.body()
        except Exception:
            return None

        # 将 body 缓存回 request，让下游 FastAPI 能再次读取
        # starlette/requests 在 body() 被调用后会缓存到 request._body
        if not hasattr(request, "_body"):
            try:
                # 兼容 starlette Request: 直接设置缓存字段
                request._body = body_bytes  # type: ignore[attr-defined]
            except Exception:
                pass

        if not body_bytes:
            return None

        try:
            parsed = json.loads(body_bytes.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """从请求中提取客户端真实 IP 地址。"""
        forwarded: str | None = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip: str | None = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host

        return "unknown"


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件。

    全局统一拦截 404、405、500、限流、权限异常，全部封装为标准错误返回格式，
    不向前端暴露原生服务报错堆栈。

    Attributes:
        app: ASGI 应用实例
    """

    def __init__(self, app: ASGIApp) -> None:
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
            request_id = getattr(request.state, "request_id", "-")
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
        """创建标准化错误响应。"""
        response_data: dict[str, Any] = {
            "code": status_code,
            "message": message,
            "data": None,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
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
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter: Limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit.per_minute}/minute"],
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return limiter


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件基础封装。

    提供请求认证的基础框架，验证 Authorization 请求头。
    可配置跳过路径列表（如健康检查、文档等）。

    此中间件为骨架实现，仅校验 Authorization 头是否存在。
    完整 JWT/OAuth 校验需要接入具体的认证服务实现。

    Attributes:
        skip_paths: 不需要认证的路径列表
    """

    def __init__(
        self,
        app: ASGIApp,
        skip_paths: list[str] | None = None,
        token_validator: Callable[[str], bool] | None = None,
    ) -> None:
        """初始化认证中间件。

        Args:
            app: ASGI 应用实例
            skip_paths: 不需要认证的路径前缀列表
            token_validator: 自定义 token 校验回调，接收 token 字符串返回是否合法
        """
        super().__init__(app)
        self.skip_paths: list[str] = skip_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/version",
        ]
        self.token_validator: Callable[[str], bool] | None = token_validator

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

        authorization: str | None = request.headers.get("Authorization")
        if not authorization or not authorization.strip():
            from src.core.exceptions import AuthenticationException

            raise AuthenticationException("Missing Authorization header")

        if self.token_validator is not None:
            token: str = (
                authorization[7:].strip()
                if authorization.lower().startswith("bearer ")
                else authorization
            )
            if not self.token_validator(token):
                from src.core.exceptions import AuthenticationException

                raise AuthenticationException("Invalid token")

        return await call_next(request)


__all__ = [
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "ExceptionHandlingMiddleware",
    "setup_rate_limiter",
    "AuthMiddleware",
]
