#!/usr/bin/env python3
"""
菜单数据访问实现
本模块提供菜单 Repository 的 SQLAlchemy 数据库实现，
仅负责菜单表的基础查询，不包含任何业务过滤/树构建逻辑。
分层约束：
    Repository 仅依赖 ORM Entity 与异常体系，不依赖任何 API Schema；
    菜单树的权限过滤与树形组装由 Service 层完成。

Classes:
    MenuRepository: 菜单数据访问 SQLAlchemy 实现
"""

from sqlalchemy import select

from src.constants.constants import MENU_STATUS_ENABLED
from src.models.entities.menu_entity import MenuEntity
from src.repositories.base_repository import BaseRepository


class MenuRepository(BaseRepository[MenuEntity, int]):
    """菜单数据访问 SQLAlchemy 实现。"""

    model_class = MenuEntity

    def list_enabled(self) -> list[MenuEntity]:
        """查询所有启用状态的菜单（按排序号与主键升序）。"""
        stmt = (
            select(MenuEntity)
            .where(MenuEntity.status == MENU_STATUS_ENABLED)
            .order_by(MenuEntity.sort_order, MenuEntity.id)
        )
        return list(self.session.execute(stmt).scalars().all())
