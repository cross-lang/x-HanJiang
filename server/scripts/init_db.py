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

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.logger import logger, setup_logging
from src.infras.database import Base, get_cached_database_provider, init_db
from src.models.entities.user_entity import UserEntity  # noqa: F401  确保模型被注册


def main() -> None:
    """主函数：初始化数据库。"""
    setup_logging()

    logger.info("=" * 60)
    logger.info("数据库初始化开始")
    logger.info("=" * 60)

    if not settings.database.url:
        logger.error("DATABASE_URL 配置不能为空，请在配置文件或环境变量中设置")
        sys.exit(1)

    logger.info(f"数据库地址: {settings.database.url}")
    logger.info(f"连接池大小: {settings.database.pool_size}")

    try:
        init_db()

        engine = get_cached_database_provider().get_engine()
        tables = Base.metadata.tables.keys()

        logger.info("=" * 60)
        logger.info("数据库初始化完成")
        logger.info("=" * 60)
        logger.info(f"已创建的表: {', '.join(tables) if tables else '(无)'}")

        logger.info("\n表结构信息:")
        for table_name in tables:
            table = Base.metadata.tables[table_name]
            logger.info(f"\n  表名: {table_name}")
            for column in table.columns:
                logger.info(f"    - {column.name}: {column.type} (主键: {column.primary_key})")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()