# -*- coding: utf-8 -*-
"""
核心基础设施包

提供应用程序运行所需的核心组件：
    - config: 配置管理
    - logger: 日志管理
    - exceptions: 异常处理
    - container: 依赖注入容器
    - middleware: HTTP 中间件
"""

from src.core.config import Settings, settings
from src.core.logger import logger, setup_logging
from src.core.exceptions import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    BusinessException,
    DatabaseException,
    ExternalServiceException,
    NotFoundException,
    SystemException,
    ValidationException,
    register_exception_handlers,
)
from src.core.container import (
    Container,
    DependencyNotFoundError,
    CircularDependencyError,
    Lifecycle,
)
from src.core.middleware import RequestIDMiddleware, AuthMiddleware

__all__ = [
    "Settings",
    "settings",
    "logger",
    "setup_logging",
    "AppException",
    "AuthenticationException",
    "AuthorizationException",
    "BusinessException",
    "DatabaseException",
    "ExternalServiceException",
    "NotFoundException",
    "SystemException",
    "ValidationException",
    "register_exception_handlers",
    "Container",
    "DependencyNotFoundError",
    "CircularDependencyError",
    "Lifecycle",
    "RequestIDMiddleware",
    "AuthMiddleware",
]
