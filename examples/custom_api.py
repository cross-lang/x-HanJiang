#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义 API 端点示例

本示例展示如何基于汉匠（HanJiang）的三层架构添加自定义 API 端点：
    1. 在 src/models/ 定义数据模型
    2. 在 src/repositories/ 实现数据访问
    3. 在 src/services/ 实现业务逻辑
    4. 在 src/api/ 定义路由端点
    5. 在 src/api/router.py 注册路由

本文件本身是一个可直接运行的演示，展示了 Product 资源的内存版实现。
实际项目中应：
    - 在 src/models/entities/ 定义 ORM 模型
    - 在 src/repositories/ 实现 SQLAlchemy 数据访问
    - Service 层承担 Entity ↔ Schema 转换
    - API 层仅做参数注入和响应包装

Usage:
    uv run python examples/custom_api.py
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# Schemas
# ============================================================


class ProductCreateRequest(BaseModel):
    """产品创建请求。"""

    name: str = Field(min_length=1, max_length=200, description="产品名称")
    price: float = Field(gt=0, description="产品价格")
    description: Optional[str] = Field(default=None, description="产品描述")


class ProductResponse(BaseModel):
    """产品响应。"""

    id: int = Field(description="产品 ID")
    name: str = Field(description="产品名称")
    price: float = Field(description="产品价格")
    description: Optional[str] = Field(default=None, description="产品描述")


# ============================================================
# Repository（内存版示例，生产环境请使用 SQLAlchemy 实现）
# ============================================================


class ProductRepository:
    """产品数据访问（内存版）。"""

    def __init__(self) -> None:
        self._storage: dict[int, dict[str, Any]] = {}
        self._next_id: int = 1

    def get_by_id(self, id: int) -> Optional[dict[str, Any]]:
        return self._storage.get(id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        items = list(self._storage.values())[skip : skip + limit]
        return items

    def create(self, data: ProductCreateRequest) -> dict[str, Any]:
        product_id = self._next_id
        self._next_id += 1
        record = {"id": product_id, **data.model_dump()}
        self._storage[product_id] = record
        return record

    def delete(self, id: int) -> bool:
        return self._storage.pop(id, None) is not None

    def count(self) -> int:
        return len(self._storage)


# ============================================================
# Service
# ============================================================


class ProductService:
    """产品业务逻辑。"""

    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    def create(self, data: dict[str, Any]) -> ProductResponse:
        request = ProductCreateRequest(**data)
        record = self._repo.create(request)
        return ProductResponse(**record)

    def get_by_id(self, id: int) -> Optional[ProductResponse]:
        record = self._repo.get_by_id(id)
        return ProductResponse(**record) if record else None

    def get_all(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        skip = (page - 1) * page_size
        items = self._repo.get_all(skip=skip, limit=page_size)
        return {
            "items": [ProductResponse(**it) for it in items],
            "total": self._repo.count(),
            "page": page,
            "page_size": page_size,
        }


# ============================================================
# Demo
# ============================================================


def main() -> None:
    """演示自定义资源的三层调用。"""
    repo = ProductRepository()
    service = ProductService(repo)

    product = service.create(
        {"name": "Widget", "price": 9.99, "description": "A useful widget"}
    )
    print(f"Created product: id={product.id} name={product.name}")

    found = service.get_by_id(product.id)
    print(f"Found product: {found.model_dump() if found else 'Not found'}")

    listing = service.get_all(page=1, page_size=10)
    print(f"Total products: {listing['total']}")


if __name__ == "__main__":
    main()