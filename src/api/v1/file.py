#!/usr/bin/env python3
"""文件管理接口。"""

from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile

from src.api.dependencies import get_file_service, require_user_permission
from src.api.response import success_response
from src.services.file_service import FileStorageService

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post(
    "/upload",
    summary="上传文件",
    description=(
        "使用 multipart/form-data 上传一个文件。文件会保存到对象存储或本地存储，"
        "接口返回文件名、存储路径、访问地址和文件大小。"
    ),
)
async def upload_file(
    request: Request,
    file: UploadFile = File(
        ...,
        description="要上传的文件，表单字段名必须是 file。",
    ),
    folder: str = Query(
        default="general",
        description=(
            "文件保存目录或对象存储前缀，例如 avatars、documents。"
            "不需要填写开头或结尾的斜杠；不传时使用 general。"
        ),
        examples=["avatars"],
    ),
    service: FileStorageService = Depends(get_file_service),
    _=Depends(require_user_permission("file:create")),
):
    return service.upload_file(file, folder)


@router.get(
    "/{file_path:path}",
    summary="获取文件",
    description="根据文件路径下载或访问文件。",
)
async def get_file(
    file_path: str = Path(..., description="文件路径"),
    service: FileStorageService = Depends(get_file_service),
    _=Depends(require_user_permission("file:view")),
):
    return service.download_file(file_path)
