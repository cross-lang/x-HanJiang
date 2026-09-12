#!/usr/bin/env python3
"""文件上传接口。"""

from fastapi import APIRouter, Depends, File, Request, UploadFile

from src.api.dependencies import get_current_user, get_file_service, get_operator_context
from src.api.response import success_response
from src.schemas.auth import CurrentUserResponse
from src.services.file_service import FileStorageService

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    summary="上传文件",
    description="上传文件到对象存储/本地存储",
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder: str = "general",
    service: FileStorageService = Depends(get_file_service),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    result = service.save_upload(file, folder=folder, operator=get_operator_context(current_user))
    return success_response(result, request)
