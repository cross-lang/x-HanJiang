#!/usr/bin/env python3
"""
用户接口

提供用户管理的 RESTful API 端点（需登录）。

Endpoints:
    POST   /users:      创建用户
    GET    /users:      查询用户列表（分页/过滤）
    GET    /users/export: 导出用户列表（CSV 文件下载，支持筛选）
    GET    /users/{id}: 查询单个用户
    POST   /users/{id}/update: 更新用户信息
    POST   /users/{id}/delete: 删除用户（软删除）
"""

import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_user_service
from src.api.response import success_response
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _page_result(result: dict) -> dict:
    """计算分页元数据。"""
    total_pages = (
        (result["total"] + result["page_size"] - 1) // result["page_size"]
        if result["page_size"] > 0
        else 0
    )
    return {
        "items": [item.model_dump() for item in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": total_pages,
    }


@router.post(
    "",
    summary="创建用户",
    description="创建一个新用户（校验租户配额、用户名租户内唯一、邮箱全局唯一）",
    status_code=201,
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    operator: dict = Depends(get_operator_context),
):
    """创建用户接口。"""
    result = service.create(body.model_dump(), operator=operator)
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "",
    summary="用户列表",
    description="查询用户列表（分页，支持租户/关键字/状态过滤）",
)
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    tenant_id: int | None = None,
    keyword: str | None = None,
    status: str | None = None,
    service: UserService = Depends(get_user_service),
):
    """用户列表接口。"""
    result = service.search(
        tenant_id=tenant_id,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )
    page_result = PaginatedResponse[UserResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"]
            if result["page_size"] > 0
            else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/export",
    summary="导出用户列表",
    description="按筛选条件导出全部匹配用户为 CSV 文件（支持租户/关键字/状态过滤）",
)
async def export_users(
    tenant_id: int | None = None,
    keyword: str | None = None,
    status: str | None = None,
    service: UserService = Depends(get_user_service),
):
    """导出用户列表接口（CSV 文件下载）。"""
    rows = service.export_users(tenant_id=tenant_id, keyword=keyword, status=status)

    fieldnames = [
        "username",
        "email",
        "role_name",
        "tenant_name",
        "status",
        "last_login_at",
    ]
    headers_cn = {
        "username": "用户名",
        "email": "邮箱",
        "role_name": "角色",
        "tenant_name": "所属租户",
        "status": "状态",
        "last_login_at": "最后登录",
    }

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writerow(headers_cn)
    for row in rows:
        writer.writerow(row)

    # utf-8-sig 保证 Excel 正确识别中文
    content = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"},
    )


@router.get(
    "/{user_id}",
    summary="查询用户",
    description="根据 ID 查询用户详情",
)
async def get_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
):
    """查询单个用户接口。"""
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(user_id)
    if result is None:
        raise NotFoundException(message=f"用户 {user_id} 不存在")
    return success_response(result.model_dump(), request)


@router.post(
    "/{user_id}/update",
    summary="更新用户",
    description="更新用户信息（密码提供时重新哈希）",
)
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    operator: dict = Depends(get_operator_context),
):
    """更新用户接口。"""
    result = service.update(
        user_id, body.model_dump(exclude_unset=True), operator=operator
    )
    return success_response(result.model_dump(), request)


@router.post(
    "/{user_id}/delete",
    summary="删除用户",
    description="根据 ID 软删除用户",
)
async def delete_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
    operator: dict = Depends(get_operator_context),
):
    """删除用户接口。"""
    service.delete(user_id, operator=operator)
    return success_response({"message": "用户删除成功"}, request)
