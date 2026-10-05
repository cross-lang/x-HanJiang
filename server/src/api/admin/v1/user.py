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
    POST   /users/{id}/reset-password: 重置用户密码
    POST   /users/{id}/delete: 删除用户（软删除）
    POST   /users/import:   批量导入用户
"""

from fastapi import APIRouter, Depends, File, Request, UploadFile

from src.api.admin.permission_decorator import permission
from src.api.admin.dependencies import (
    get_current_user,
    get_user_operator_context,
    get_user_service,
    require_user_permission,
)
from src.api.response import success_response
from src.constants.enums import Gender, UserStatus
from src.constants.permissions import PermissionCode
from src.core.exceptions import ValidationException
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.user import (
    AdminResetPasswordRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from src.schemas.common import PaginatedResponse
from src.services.user_service import UserService
from src.utils.csv import build_csv_stream_response, parse_csv_rows

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.post(
    "",
    summary="创建用户",
    description="创建一个新用户（校验邮箱/用户名全局唯一）",
    status_code=201,
    dependencies=[Depends(require_user_permission(PermissionCode.USER_CREATE.mark))],
)
@permission(PermissionCode.USER_CREATE)
def create_user(
    body: UserCreateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = service.create(body.model_dump(), operator=get_user_operator_context(current_user, request))
    return success_response(result.model_dump(), request, code=201)


@router.get(
    "",
    summary="用户列表",
    description="查询用户列表（分页，支持关键字/状态过滤）",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_VIEW.mark))],
)
@permission(PermissionCode.USER_VIEW)
def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = service.search(keyword=keyword, status=status, page=page, page_size=page_size)
    page_result = PaginatedResponse[UserResponse](
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=(
            (result["total"] + result["page_size"] - 1) // result["page_size"] if result["page_size"] > 0 else 0
        ),
    )
    return success_response(page_result.model_dump(), request)


@router.get(
    "/export",
    summary="导出用户列表",
    description="按筛选条件导出全部匹配用户为 CSV 文件（支持关键字/状态过滤）",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_EXPORT.mark))],
)
@permission(PermissionCode.USER_EXPORT)
def export_users(
    keyword: str | None = None,
    status: str | None = None,
    service: UserService = Depends(get_user_service),
):
    rows = service.search(keyword=keyword, status=status, page=1, page_size=100000)["items"]
    fieldnames = [
        "id",
        "username",
        "name",
        "email",
        "phone",
        "gender",
        "birthday",
        "roles",
        "status",
        "last_login_at",
        "created_at",
    ]
    headers_cn = {
        "id": "ID",
        "username": "用户名",
        "name": "姓名",
        "email": "邮箱",
        "phone": "手机号",
        "gender": "性别",
        "birthday": "生日",
        "roles": "角色",
        "status": "状态",
        "last_login_at": "最后登录",
        "created_at": "创建时间",
    }
    csv_rows = []
    for row in rows:
        data = row.model_dump()
        if isinstance(data.get("roles"), list):
            data["roles"] = ";".join(r.get("role_name", "") for r in data["roles"])
        data["gender"] = Gender.get_desc_by_mark(data["gender"]) if data.get("gender") else ""
        data["status"] = UserStatus.get_desc_by_mark(data["status"], default=data.get("status") or "")
        csv_rows.append(data)
    return build_csv_stream_response(
        fieldnames=fieldnames,
        headers_cn=headers_cn,
        rows=csv_rows,
        filename="users_export.csv",
    )


@router.get(
    "/{user_id}",
    summary="查询用户",
    description="根据 ID 查询用户详情",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_VIEW.mark))],
)
@permission(PermissionCode.USER_VIEW)
def get_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
):
    from src.core.exceptions import NotFoundException

    result = service.get_by_id(user_id)
    if result is None:
        raise NotFoundException(message=f"用户 {user_id} 不存在")
    return success_response(result.model_dump(), request)


@router.post(
    "/{user_id}/update",
    summary="更新用户",
    description="更新用户信息（密码提供时重新哈希）",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_EDIT.mark))],
)
@permission(PermissionCode.USER_EDIT)
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = service.update(
        user_id, body.model_dump(exclude_unset=True), operator=get_user_operator_context(current_user, request)
    )
    return success_response(result.model_dump(), request)


@router.post(
    "/{user_id}/reset-password",
    summary="重置用户密码",
    description="管理员重置指定用户的密码",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_EDIT.mark))],
)
@permission(PermissionCode.USER_EDIT)
def reset_user_password(
    user_id: int,
    body: AdminResetPasswordRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    service.reset_password(user_id, body.new_password, operator=get_user_operator_context(current_user, request))
    return success_response({"message": "密码重置成功"}, request)


@router.post(
    "/{user_id}/delete",
    summary="删除用户",
    description="根据 ID 软删除用户",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_DELETE.mark))],
)
@permission(PermissionCode.USER_DELETE)
def delete_user(
    user_id: int,
    request: Request,
    service: UserService = Depends(get_user_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    service.delete(user_id, operator=get_user_operator_context(current_user, request))
    return success_response({"message": "用户删除成功"}, request)


@router.post(
    "/import",
    summary="导入用户列表",
    description="上传 CSV 文件批量导入用户（基础版本）",
    dependencies=[Depends(require_user_permission(PermissionCode.USER_IMPORT.mark))],
)
@permission(PermissionCode.USER_IMPORT)
def import_users(
    request: Request,
    file: UploadFile = File(...),
    service: UserService = Depends(get_user_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationException(message="仅支持 CSV 文件导入")
    csv_content = file.file.read().decode("utf-8-sig")
    rows = parse_csv_rows(csv_content)
    operator_ctx = get_user_operator_context(current_user, request)
    result = service.import_users(rows, operator=operator_ctx)
    return success_response({"imported": result["imported"], "filename": file.filename}, request)
