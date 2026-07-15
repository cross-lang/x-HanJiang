#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义 API 端点示例

本示例展示如何基于寒江（HanJiang） 的三层架构添加自定义 API 端点。
按照以下步骤可快速扩展新的业务接口：

1. 在 src/models/ 定义数据模型
2. 在 src/repositories/ 实现数据访问
3. 在 src/services/ 实现业务逻辑
4. 在 src/api/ 定义路由端点
5. 在 src/api/router.py 注册路由

Usage:
    参考本示例中的代码结构，创建你自己的业务接口。
"""


# ============================================================
# Step 1: 定义数据模型（src/models/product.py）
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional


class ProductCreateRequest(BaseModel):
    """产品创建请求模型。"""

    name: str = Field(min_length=1, max_length=200, description="产品名称")
    price: float = Field(gt=0, description="产品价格")
    description: Optional[str] = Field(default=None, description="产品描述")


class ProductResponse(BaseModel):
    """产品响应模型。"""

    id: int = Field(description="产品 ID")
    name: str = Field(description="产品名称")
    price: float = Field(description="产品价格")
    description: Optional[str] = Field(default=None, description="产品描述")


# ============================================================
# Step 2: 实现 Repository（src/repositories/product_repository.py）
# ============================================================

from src.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[ProductResponse, int]):
    """产品数据访问实现。"""

    def __init__(self) -> None:
        self._storage: dict[int, dict] = {}
        self._next_id: int = 1

    def get_by_id(self, id: int) -> Optional[ProductResponse]:
        data = self._storage.get(id)
        return ProductResponse(**data) if data else None

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ProductResponse]:
        items = list(self._storage.values())[skip : skip + limit]
        return [ProductResponse(**item) for item in items]

    def create(self, entity: ProductCreateRequest) -> ProductResponse:
        product_id = self._next_id
        self._next_id += 1
        data = {"id": product_id, **entity.model_dump()}
        self._storage[product_id] = data
        return ProductResponse(**data)

    def update(self, id: int, entity) -> Optional[ProductResponse]:
        if id not in self._storage:
            return None
        self._storage[id].update(entity.model_dump(exclude_unset=True))
        return ProductResponse(**self._storage[id])

    def delete(self, id: int) -> bool:
        if id not in self._storage:
            return False
        del self._storage[id]
        return True

    def count(self) -> int:
        return len(self._storage)


# ============================================================
# Step 3: 实现 Service（src/services/product_service.py）
# ============================================================

from src.services.base_service import BaseService


class ProductService(BaseService[ProductResponse, int]):
    """产品业务逻辑。"""

    def __init__(self, product_repository: ProductRepository) -> None:
        self._repo = product_repository

    def get_by_id(self, id: int) -> Optional[ProductResponse]:
        return self._repo.get_by_id(id)

    def get_all(self, page: int = 1, page_size: int = 20) -> dict:
        skip = (page - 1) * page_size
        items = self._repo.get_all(skip=skip, limit=page_size)
        return {"items": items, "total": self._repo.count(), "page": page, "page_size": page_size}

    def create(self, data: dict) -> ProductResponse:
        request = ProductCreateRequest(**data)
        return self._repo.create(request)

    def update(self, id: int, data: dict) -> Optional[ProductResponse]:
        return self._repo.update(id, data)

    def delete(self, id: int) -> bool:
        return self._repo.delete(id)


# ============================================================
# Step 4: 定义 API 路由（src/api/product.py）
# ============================================================

from fastapi import APIRouter, Request

# router = APIRouter(prefix="/products", tags=["products"])
#
# @router.post("")
# async def create_product(body: ProductCreateRequest, request: Request):
#     service = ProductService(ProductRepository())
#     result = service.create(body.model_dump())
#     return success(data=result.model_dump())
#
# @router.get("")
# async def list_products(request: Request, page: int = 1, page_size: int = 20):
#     service = ProductService(ProductRepository())
#     result = service.get_all(page=page, page_size=page_size)
#     items = [item.model_dump() for item in result["items"]]
#     return success(data={"items": items, "total": result["total"]})


# ============================================================
# Step 5: 在 src/api/router.py 中注册路由
# ============================================================

# api_router.include_router(product.router)


def main() -> None:
    """运行自定义 API 示例。"""
    repo = ProductRepository()

    # 创建产品
    product_data = ProductCreateRequest(name="Widget", price=9.99, description="A useful widget")
    product = repo.create(product_data)
    print(f"Created product: {product.model_dump()}")

    # 查询产品
    found = repo.get_by_id(product.id)
    print(f"Found product: {found.model_dump() if found else 'Not found'}")

    # 统计数量
    print(f"Total products: {repo.count()}")


if __name__ == "__main__":
    main()
