#!/usr/bin/env python3
"""
种子数据初始化

应用启动时检测并自动创建系统内置种子数据：
    1. 超级管理员角色（roles 表，role_type=system，role_code=super_admin）
    2. 超级管理员用户（users 表，username=superadmin，绑定上述角色）

若数据已存在则跳过，保证幂等。

Functions:
    init_seed_data: 初始化种子数据（幂等）
"""

from datetime import UTC, datetime

from sqlalchemy import select

from src.core.exceptions import DatabaseException
from src.core.logger import logger
from src.core.security import hash_password
from src.infras.mysql import get_session_factory
from src.models.entities.user_entity import RoleEntity, UserEntity

# 种子数据常量（系统内置，禁止随意修改）
_SEED_ROLE_CODE = "super_admin"
_SEED_ROLE_NAME = "超级管理员"
_SEED_ADMIN_USERNAME = "superadmin"
_SEED_ADMIN_PASSWORD = "admin@123456"
_SEED_ADMIN_EMAIL = "superadmin@system.local"


def init_seed_data() -> None:
    """初始化系统种子数据（幂等，可重复调用）。

    检测顺序：
        1. roles 表中是否存在 role_code=super_admin 的角色，无则创建
        2. users 表中是否存在 username=superadmin 的用户，无则创建（绑定超管角色）
    """
    session = get_session_factory()()
    try:
        # 1. 超级管理员角色
        role = session.execute(
            select(RoleEntity).where(RoleEntity.role_code == _SEED_ROLE_CODE)
        ).scalars().first()

        if role is None:
            role = RoleEntity(
                role_name=_SEED_ROLE_NAME,
                role_code=_SEED_ROLE_CODE,
                description="系统内置超级管理员角色，拥有全部权限",
                role_type="system",
                status="enabled",
            )
            session.add(role)
            session.flush()
            logger.info(f"Seed role created: role_code={_SEED_ROLE_CODE}")
        else:
            logger.info(f"Seed role already exists: role_code={_SEED_ROLE_CODE}")

        # 2. 超级管理员用户
        admin = session.execute(
            select(UserEntity).where(UserEntity.username == _SEED_ADMIN_USERNAME)
        ).scalars().first()

        if admin is None:
            admin = UserEntity(
                username=_SEED_ADMIN_USERNAME,
                email=_SEED_ADMIN_EMAIL,
                password_hash=hash_password(_SEED_ADMIN_PASSWORD),
                phone=None,
                avatar_url=None,
                role_id=role.id,
                status="active",
            )
            session.add(admin)
            session.flush()
            logger.info(f"Seed admin user created: username={_SEED_ADMIN_USERNAME}")
        else:
            logger.info(
                f"Seed admin user already exists: username={_SEED_ADMIN_USERNAME}"
            )

        session.commit()
        logger.info("Seed data initialization completed")
    except Exception as e:  # noqa: BLE001
        session.rollback()
        logger.warning(f"Seed data initialization skipped: {e}")
        # 种子初始化失败不应阻断应用启动
    finally:
        session.close()
