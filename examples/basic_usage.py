#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础使用示例

本示例展示如何导入和使用寒江（HanJiang） 的核心模块。

Usage:
    uv run python examples/basic_usage.py
"""

from src.core.config import settings
from src.core.logger import setup_logging, logger
from src.common.constants import APP_NAME, APP_VERSION
from src.common.response import success, error


def main() -> None:
    """基础使用示例主函数。"""
    # 1. 初始化日志
    setup_logging()

    # 2. 读取配置
    logger.info(f"应用名称: {APP_NAME}")
    logger.info(f"应用版本: {APP_VERSION}")
    logger.info(f"运行环境: {settings.APP_ENV}")
    logger.info(f"监听端口: {settings.server.SERVER_PORT}")
    logger.info(f"调试模式: {settings.server.SERVER_DEBUG}")

    # 3. 构建响应
    success_resp = success(data={"message": "Hello, 寒江（HanJiang）!"})
    logger.info(f"成功响应: {success_resp}")

    error_resp = error(code=400, message="参数错误")
    logger.warning(f"错误响应: {error_resp}")

    # 4. 使用日志绑定 request_id
    logger.bind(request_id="demo-request-001").info("这是一条带请求 ID 的日志")

    logger.info("基础使用示例运行完成！")


if __name__ == "__main__":
    main()
