#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理模块

本模块提供全局唯一日志实例，基于 loguru 实现，支持：
    - 日志分级：DEBUG / INFO / WARNING / ERROR / CRITICAL
    - 文件 + 控制台双输出
    - 日志轮转和自动清理（按小时切割）
    - 请求 ID 追踪
    - 通过 Settings 配置日志参数，禁止硬编码
    - 日志命名规范：项目名称-YYYYMMDDhh.log

Usage:
    from src.core.logger import logger, setup_logging

    # 在应用启动时调用一次
    setup_logging()

    # 在任意模块中使用
    logger.info("Application started")
    logger.bind(request_id="xxx").info("Request received")
"""

import os
import sys
from typing import Optional

from loguru import logger as _logger

from src.constants import APP_NAME

_logger.remove()

_configured: bool = False

_LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[request_id]} | "
    "<level>{message}</level>"
)

_DEFAULT_REQUEST_ID: str = "-"


def setup_logging(
    level: Optional[str] = None,
    file_path: Optional[str] = None,
    rotation: Optional[str] = None,
    retention: Optional[str] = None,
) -> None:
    """初始化日志配置，全局只能调用一次。

    参数为 None 时，从 Settings 加载默认值。在应用 lifespan 中调用。

    Args:
        level: 日志级别，如 DEBUG、INFO、WARNING、ERROR、CRITICAL
        file_path: 日志文件路径
        rotation: 日志轮转周期，如 "1 hour"、"1 day"、"100 MB"
        retention: 日志保留时间，如 "7 days"、"30 days"
    """
    global _configured

    if _configured:
        return

    from src.core.config import settings

    log_level: str = level or settings.logging.level
    log_file_path: str = file_path or settings.logging.file_path
    log_rotation: str = rotation or settings.logging.rotation
    log_retention: str = retention or settings.logging.retention

    log_dir: str = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    _logger.remove()

    _logger.add(
        sink=sys.stderr,
        format=_LOG_FORMAT,
        level=log_level,
        colorize=True,
        enqueue=True,
    )

    _logger.add(
        sink=log_file_path,
        format=_LOG_FORMAT,
        level=log_level,
        rotation=log_rotation,
        retention=log_retention,
        compression="zip",
        enqueue=True,
        serialize=False,
    )

    _logger.configure(
        patcher=lambda record: record["extra"].setdefault(
            "request_id", _DEFAULT_REQUEST_ID
        )
    )

    _configured = True


def get_logger() -> _logger.__class__:
    """获取全局日志实例。

    Returns:
        loguru.Logger: 全局日志实例
    """
    return _logger


def get_log_file_path() -> str:
    """获取日志文件路径，按小时切割时使用项目名称作为前缀。

    Returns:
        str: 日志文件路径
    """
    from src.core.config import settings

    base_path: str = settings.logging.file_path
    if base_path:
        dir_path: str = os.path.dirname(base_path)
        ext: str = os.path.splitext(base_path)[1] or ".log"
        return os.path.join(dir_path, f"{APP_NAME}-{{time:YYYYMMDDHH}}{ext}")
    return f"logs/{APP_NAME}-{{time:YYYYMMDDHH}}.log"


logger = _logger

__all__ = ["logger", "setup_logging", "get_logger", "get_log_file_path"]