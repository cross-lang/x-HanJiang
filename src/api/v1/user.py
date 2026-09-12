#!/usr/bin/env python3
"""
用户接口

提供用户管理的 RESTful API 端点。

Endpoints:
    POST   /users:          创建用户
    GET    /users:          查询用户列表（分页/过滤）
    GET    /users/export:   导出用户列表（CSV 文件下载，支持筛选）
    GET    /users/{id}:     查询单个用户
    POST   /users/{id}/update: 更新用户信息
    POST   /users/{id}/delete: 删除用户（软删除）
"""

import csv
import io

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.api.dependencies import (
    get_current_user,
    get_operator_context,
    get_user_service,
)
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    summary="创建用户",
    description="创建一个新用户（校验邮箱/用户名全局唯一）",
    status_code=201,
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """创建用户接口。"""
    result = service.create(body.model_dump(), operator=get_operator_context(current_user))
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "",
    summary="用户列表",
    description="查询用户列表（分页，支持关键字/状态过滤）",
)
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """用户列表接口。"""
    result = service.search(
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
    description="按筛选条件导出全部匹配用户为 CSV 文件（支持关键字/状态过滤）",
)
async def export_users(
    keyword: str | None = None,
    status: str | None = None,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """导出用户列表接口（CSV 文件下载）。"""
    rows = service.search(keyword=keyword, status=status, page=1, page_size=100000)[
        "items"
    ]

    fieldnames = [
        "id",
        "username",
        "email",
        "phone",
        "status",
        "last_login_at",
        "created_at",
    ]
    headers_cn = {
        "id": "ID",
        "username": "用户名",
        "email": "邮箱",
        "phone": "手机号",
        "status": "状态",
        "last_login_at": "最后登录",
        "created_at": "创建时间",
    }

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writerow(headers_cn)
    for row in rows:
        data = row.model_dump()
        writer.writerow({k: data.get(k, "") for k in fieldnames})

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
    current_user: CurrentUserResponse = Depends(get_current_user),
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
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """更新用户接口。"""
    result = service.update(
        user_id,
        body.model_dump(exclude_unset=True),
        operator=get_operator_context(current_user),
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
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """删除用户接口。"""
    service.delete(user_id, operator=get_operator_context(current_user))
    return success_response({"message": "用户删除成功"}, request)


@router.post(
    "/import",
    summary="导入用户列表",
    description="上传 CSV 文件批量导入用户（基础版本）",
)
async def import_users(
    request: Request,
    file: UploadFile = File(...),
    service: UserService = Depends(get_user_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """导入用户列表接口（CSV）。"""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValueError("仅支持 CSV 文件导入")

    csv_content = (await file.read()).decode("utf-8-sig")
    rows = list(csv.DictReader(csv_content.splitlines()))

    imported = 0
    operator_ctx = get_operator_context(current_user)
    for row in rows:
        if not row.get("username") or not row.get("email"):
            continue
        payload = {
            "username": row["username"],
            "email": row["email"],
            "password": row.get("password") or "ChangeMe@123",
            "phone": row.get("phone"),
            "avatar_url": row.get("avatar_url"),
            "role_id": int(row["role_id"]) if row.get("role_id") else None,
            "status": row.get("status") or "active",
        }
        service.create(payload, operator=operator_ctx)
        imported += 1

    return success_response({"imported": imported, "filename": file.filename}, request)
