#!/usr/bin/env python3
"""文件管理接口。"""

from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile

from src.api.dependencies import get_current_user, get_file_service, get_operator_context
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
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
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    result = service.save_upload(file, folder=folder, operator=get_operator_context(current_user))
    return success_response(result, request)


@router.get(
    "/{file_path:path}",
    summary="下载文件",
    description=(
        "根据上传接口返回的 path 或 key 下载文件。file_path 可以包含多级目录，"
        "例如 avatars/user-1.png。不要传完整 URL，也不要传以 /files/ 开头的 URL 路径。"
    ),
)
async def download_file(
    file_path: str = Path(
        ...,
        description=(
            "文件相对路径，通常使用上传接口返回结果中的 path 或 key。"
            "支持多级目录，例如 documents/report.pdf。"
        ),
        examples=["documents/report.pdf"],
    ),
    service: FileStorageService = Depends(get_file_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    return service.download_file(file_path)
