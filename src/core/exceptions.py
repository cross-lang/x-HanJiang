#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理模块

本模块定义了应用程序的异常层级结构和全局异常处理器。
所有自定义异常继承自 AppException，分为业务异常（4xx）和系统异常（5xx）两类。

异常层级：
    AppException                          # 应用异常基类
    ├── BusinessException                 # 业务异常 (4xx)
    │   ├── ValidationException           # 参数校验异常 (422)
    │   ├── AuthenticationException       # 认证异常 (401)
    │   ├── AuthorizationException        # 授权异常 (403)
    │   └── NotFoundException             # 资源未找到 (404)
    └── SystemException                   # 系统异常 (5xx)
        ├── DatabaseException             # 数据库异常 (500)
        └── ExternalServiceException      # 外部服务异常 (502)

Usage:
    from src.core.exceptions import BusinessException, register_exception_handlers

    # 在业务代码中抛出异常
    raise BusinessException("Order not found")

    # 在 FastAPI 应用中注册全局处理器
    register_exception_handlers(app)
"""

import datetime
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.constants import MSG_INTERNAL_ERROR, MSG_VALIDATION_ERROR


class AppException(Exception):
    """应用异常基类。

    所有自定义异常必须继承此类，禁止直接使用 Python 内置异常。

    Attributes:
        message: 异常描述信息
        code: HTTP 状态码
        details: 附加详情信息
    """

    def __init__(
        self,
        message: str = "Application error",
        code: int = 500,
        details: Optional[Any] = None,
    ) -> None:
        """初始化应用异常。

        Args:
            message: 异常描述信息
            code: HTTP 状态码
            details: 附加详情（如校验错误列表）
        """
        self.message: str = message
        self.code: int = code
        self.details: Optional[Any] = details
        super().__init__(self.message)


class BusinessException(AppException):
    """业务异常基类（4xx 错误）。

    用于表示由客户端请求引起的可预期错误，如参数校验失败、资源不存在等。
    """

    def __init__(
        self,
        message: str = "Business error",
        code: int = 400,
        details: Optional[Any] = None,
    ) -> None:
        """初始化业务异常。

        Args:
            message: 异常描述信息
            code: HTTP 状态码（默认 400）
            details: 附加详情
        """
        super().__init__(message=message, code=code, details=details)


class ValidationException(BusinessException):
    """参数校验异常。

    用于请求参数不符合校验规则时抛出。
    """

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Any] = None,
    ) -> None:
        """初始化校验异常。

        Args:
            message: 异常描述信息
            details: 校验错误详情列表
        """
        super().__init__(message=message, code=422, details=details)


class AuthenticationException(BusinessException):
    """认证异常。

    用于身份认证失败时抛出（如 token 无效或过期）。
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Any] = None,
    ) -> None:
        """初始化认证异常。

        Args:
            message: 异常描述信息
            details: 附加详情
        """
        super().__init__(message=message, code=401, details=details)


class AuthorizationException(BusinessException):
    """授权异常。

    用于权限不足时抛出（如用户无权访问某资源）。
    """

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Any] = None,
    ) -> None:
        """初始化授权异常。

        Args:
            message: 异常描述信息
            details: 附加详情
        """
        super().__init__(message=message, code=403, details=details)


class NotFoundException(BusinessException):
    """资源未找到异常。

    用于请求的资源不存在时抛出。
    """

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Any] = None,
    ) -> None:
        """初始化资源未找到异常。

        Args:
            message: 异常描述信息
            details: 附加详情
        """
        super().__init__(message=message, code=404, details=details)


class SystemException(AppException):
    """系统异常基类（5xx 错误）。

    用于表示由服务端内部错误引起的不可预期异常。
    """

    def __init__(
        self,
        message: str = "Internal server error",
        code: int = 500,
        details: Optional[Any] = None,
    ) -> None:
        """初始化系统异常。

        Args:
            message: 异常描述信息
            code: HTTP 状态码（默认 500）
            details: 附加详情
        """
        super().__init__(message=message, code=code, details=details)


class DatabaseException(SystemException):
    """数据库异常。

    用于数据库操作失败时抛出。
    """

    def __init__(
        self,
        message: str = "Database error",
        details: Optional[Any] = None,
    ) -> None:
        """初始化数据库异常。

        Args:
            message: 异常描述信息
            details: 附加详情
        """
        super().__init__(message=message, code=500, details=details)


class ExternalServiceException(SystemException):
    """外部服务异常。

    用于调用外部服务（如第三方 API、消息队列）失败时抛出。
    """

    def __init__(
        self,
        message: str = "External service error",
        details: Optional[Any] = None,
    ) -> None:
        """初始化外部服务异常。

        Args:
            message: 异常描述信息
            details: 附加详情
        """
        super().__init__(message=message, code=502, details=details)


def _get_request_id(request: Request) -> Optional[str]:
    """从请求状态中获取 request_id。

    Args:
        request: FastAPI 请求对象

    Returns:
        Optional[str]: 请求 ID，如不存在则返回 None
    """
    return getattr(request.state, "request_id", None)


def _build_error_response(
    code: int,
    message: str,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    """构建错误响应字典。

    Args:
        code: HTTP 状态码
        message: 错误消息
        request_id: 请求追踪 ID

    Returns:
        dict[str, Any]: 标准化错误响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": None,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "request_id": request_id,
    }


async def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理所有 AppException 及其子类的全局异常处理器。

    Args:
        request: 当前请求对象
        exc: 捕获的应用异常

    Returns:
        JSONResponse: 标准化的错误响应
    """
    from src.core.logger import logger

    request_id: Optional[str] = _get_request_id(request)
    log_level: str = "ERROR" if exc.code >= 500 else "WARNING"
    logger.bind(request_id=request_id or "-").log(
        log_level,
        f"{type(exc).__name__}: {exc.message}",
    )

    response_data: dict[str, Any] = _build_error_response(
        code=exc.code,
        message=exc.message,
        request_id=request_id,
    )
    if exc.details is not None:
        response_data["data"] = {"details": exc.details}

    return JSONResponse(
        status_code=exc.code,
        content=response_data,
    )


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理 Pydantic 请求校验异常。

    Args:
        request: 当前请求对象
        exc: FastAPI 校验异常

    Returns:
        JSONResponse: 包含校验错误详情的标准化错误响应
    """
    from src.core.logger import logger

    request_id: Optional[str] = _get_request_id(request)
    errors: list[dict[str, Any]] = exc.errors()

    logger.bind(request_id=request_id or "-").warning(
        f"Validation error: {errors}"
    )

    response_data: dict[str, Any] = _build_error_response(
        code=422,
        message=MSG_VALIDATION_ERROR,
        request_id=request_id,
    )
    response_data["data"] = {"details": errors}

    return JSONResponse(
        status_code=422,
        content=response_data,
    )


async def _generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """处理所有未捕获的异常的兜底处理器。

    Args:
        request: 当前请求对象
        exc: 捕获的异常

    Returns:
        JSONResponse: 标准化的 500 错误响应
    """
    from src.core.logger import logger

    request_id: Optional[str] = _get_request_id(request)
    logger.bind(request_id=request_id or "-").exception(
        f"Unhandled exception: {exc}"
    )

    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            code=500,
            message=MSG_INTERNAL_ERROR,
            request_id=request_id,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 应用。

    包括 AppException 层级、Pydantic 校验异常、以及通用异常兜底处理。
    必须在 create_app() 中调用。

    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(AppException, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_exception_handler)  # type: ignore[arg-type]