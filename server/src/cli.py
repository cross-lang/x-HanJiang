#!/usr/bin/env python3
"""汉江 x-HanJiang 命令行启动入口。

用法（项目根执行，等价于 uv run x-HanJiang）：
    uv run x-HanJiang                 # 默认启动：热重载跟随 settings.server.debug
    uv run x-HanJiang --reload        # 显式开启热重载（修改代码自动重启）
    uv run x-HanJiang --no-reload     # 显式关闭热重载（生产环境）
    uv run x-HanJiang --port 8000     # 覆盖监听端口
    uv run x-HanJiang --host 0.0.0.0  # 覆盖监听地址
    uv run x-HanJiang --workers 4     # 覆盖 Worker 进程数

与 src/main.py 的分工：
    main.py 是纯应用装配模块（create_app + lifespan + app 对象），供
    gunicorn / uvicorn 命令行、测试与脚本 import；本模块是进程启动入口，
    负责命令行参数解析并委托 uvicorn 启动 "src.main:app"。
"""

from __future__ import annotations

import argparse
import sys


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数（纯函数，可独立单测）。"""
    parser = argparse.ArgumentParser(
        prog="x-HanJiang",
        description="汉江管理系统后端启动器（FastAPI + Uvicorn）",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="监听地址（默认取配置 settings.server.host）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听端口（默认取配置 settings.server.port）",
    )
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=None,
        help="开启热重载（开发环境默认开启；显式指定以覆盖默认）",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="关闭热重载",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Worker 进程数（生产多进程部署；热重载模式强制为 1）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """启动汉江后端服务。"""
    args = _parse_args(argv)

    import uvicorn

    # 延迟加载配置：确保 .env / config.yaml 已加载后再启动
    from src.core.config import settings
    from src.core.logger import logger

    host = args.host or settings.server.host
    port = args.port or settings.server.port

    # 热重载：未显式指定时跟随 settings.server.debug（开发调试默认开启）
    reload_enabled = args.reload if args.reload is not None else settings.server.debug

    workers = args.workers or settings.server.workers
    if reload_enabled and workers != 1:
        logger.warning("热重载模式不支持多 Worker，已强制为 1")
        workers = 1

    if reload_enabled:
        logger.info(f"热重载已开启（debug={settings.server.debug}）；修改代码后服务自动重启")
    logger.info(f"汉江后端启动：http://{host}:{port}  |  接口文档 http://{host}:{port}/docs")

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        workers=workers,
        log_level="info",
    )


if __name__ == "__main__":
    main(sys.argv[1:])
