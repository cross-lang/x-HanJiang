#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本

本脚本用于初始化数据库，创建所有数据表。
在生产环境中，建议使用数据库迁移工具（如 Alembic）管理表结构变更。

Usage:
    uv run python scripts/init_db.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.database import init_db, get_engine, Base
from src.models.entities.user_entity import UserEntity
from src.core.logger import setup_logging, logger


def main() -> None:
    """主函数：初始化数据库。"""
    # 初始化日志
    setup_logging()

    logger.info("=" * 60)
    logger.info("数据库初始化开始")
    logger.info("=" * 60)

    # 检查数据库配置
    if not settings.database.DATABASE_URL:
        logger.error("DATABASE_URL 配置不能为空，请在配置文件或环境变量中设置")
        sys.exit(1)

    logger.info(f"数据库地址: {settings.database.DATABASE_URL}")
    logger.info(f"连接池大小: {settings.database.DATABASE_POOL_SIZE}")

    try:
        # 初始化数据库
        init_db()

        # 列出所有创建的表
        engine = get_engine()
        tables = Base.metadata.tables.keys()

        logger.info("=" * 60)
        logger.info("数据库初始化完成")
        logger.info("=" * 60)
        logger.info(f"已创建的表: {', '.join(tables)}")

        # 显示表结构信息
        logger.info("\n表结构信息:")
        for table_name in tables:
            table = Base.metadata.tables[table_name]
            logger.info(f"\n  表名: {table_name}")
            for column in table.columns:
                logger.info(f"    - {column.name}: {column.type} (主键: {column.primary_key})")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
