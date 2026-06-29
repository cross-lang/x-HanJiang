#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理模块

本模块提供全局唯一日志实例，基于 loguru 实现，支持：
    - 日志分级：DEBUG / INFO / WARNING / ERROR / CRITICAL
    - 文件 + 控制台双输出
    - 日志轮转和自动清理
    - 请求 ID 追踪
    - 通过 Settings 配置日志参数，禁止硬编码

Usage:
    from src.core.logger import logger, setup_logging

    # 在应用启动时调用一次
    setup_logging()

    # 在任意模块中使用
    logger.info("Application started")
    logger.bind(request_id="xxx").info("Request received")
"""

import sys
from typing import Optional

from loguru import logger as _logger

# 移除 loguru 默认处理器
_logger.remove()

# 配置是否已初始化的标志
_configured: bool = False

# 日志格式模板
_LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[request_id]} | "
    "<level>{message}</level>"
)

# 当 request_id 未绑定时显示的占位符
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
        rotation: 日志轮转周期，如 "1 day"、"100 MB"
        retention: 日志保留时间，如 "7 days"、"30 days"
    """
    global _configured

    if _configured:
        return

    from src.core.config import settings
    import os

    log_level: str = level or settings.logging.LOGGING_LEVEL
    log_file_path: str = file_path or settings.logging.LOGGING_FILE_PATH
    log_rotation: str = rotation or settings.logging.LOGGING_ROTATION
    log_retention: str = retention or settings.logging.LOGGING_RETENTION

    # 确保日志目录存在
    log_dir: str = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 清除已有处理器
    _logger.remove()

    # 控制台输出
    _logger.add(
        sink=sys.stderr,
        format=_LOG_FORMAT,
        level=log_level,
        colorize=True,
        enqueue=True,
    )

    # 文件输出
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

    # 设置默认 request_id 占位符
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


# 导出日志实例
logger = _logger

__all__ = ["logger", "setup_logging", "get_logger"]
