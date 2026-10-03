#!/usr/bin/env python3
"""文件管理接口。"""

from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile

from src.api.admin.permission_decorator import permission
from src.api.dependencies import get_current_user, get_file_service, is_admin_user, require_user_permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.schemas.admin.auth import CurrentUser
from src.services.admin.file_service import FileStorageService

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post(
    "/upload",
    summary="上传文件",
    dependencies=[Depends(require_user_permission(PermissionCode.FILE_CREATE.mark))],
)
@permission(PermissionCode.FILE_CREATE)
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder: str = Query(default="general"),
    service: FileStorageService = Depends(get_file_service),
    current_user=Depends(get_current_user),
):
    result = service.save_upload(
        file,
        folder,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response(result, request, code=201)


@router.get(
    "",
    summary="文件列表",
    dependencies=[Depends(require_user_permission(PermissionCode.FILE_VIEW.mark))],
)
@permission(PermissionCode.FILE_VIEW)
def list_files(
    request: Request,
    folder: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: FileStorageService = Depends(get_file_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    # 普通用户只能看自己上传的文件
    uploaded_by = None if is_admin_user(current_user) else current_user.id
    result = service.list_files(folder=folder, keyword=keyword, page=page, page_size=page_size, uploaded_by=uploaded_by)
    return success_response(result, request)


@router.get(
    "/{file_path:path}",
    summary="获取文件",
    dependencies=[Depends(require_user_permission(PermissionCode.FILE_VIEW.mark))],
)
@permission(PermissionCode.FILE_VIEW)
def get_file(
    file_path: str = Path(...),
    service: FileStorageService = Depends(get_file_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = service.download_file(
        file_path,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return result


@router.delete(
    "/{file_id}",
    summary="删除文件",
    dependencies=[Depends(require_user_permission(PermissionCode.FILE_DELETE.mark))],
)
@permission(PermissionCode.FILE_DELETE)
def delete_file(
    file_id: int,
    request: Request,
    service: FileStorageService = Depends(get_file_service),
    current_user: CurrentUser = Depends(get_current_user),
):
    service.delete_file(
        file_id,
        operator={"operator_id": current_user.id, "operator_name": current_user.username},
    )
    return success_response({"deleted": True}, request)
