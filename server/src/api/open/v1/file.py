#!/usr/bin/env python3
"""开放平台文件管理接口。
将文件管理核心能力暴露给外部服务，通过 AppId/AppKey + scope 鉴权。
operator 上下文记录为调用方应用，而非终端用户。

上传约定：开放接口签名体系固定 Content-Type: application/json 并对 body
做 SHA256 摘要，multipart 无法进入签名串，故文件上传以 base64 内嵌 JSON
（见 schemas/open/file.py OpenFileUploadRequest）走 services.file_service.save_bytes。
"""

import base64
import binascii

from fastapi import APIRouter, Depends, Path, Query, Request

from src.api.open.dependencies import (
    CurrentApp,
    get_app_operator_context,
    get_current_app,
    get_file_service,
    require_app_scope,
)
from src.api.open.scope_decorator import app_scope
from src.api.response import success_response
from src.constants.scopes import OpenApiScopeCode
from src.core.exceptions import ValidationException
from src.schemas.common import ApiResponse
from src.schemas.open.file import OpenFileUploadRequest
from src.services.file_service import FileStorageService

router = APIRouter(prefix="/files", tags=["开放平台：文件管理"])


@router.get(
    "",
    summary="开放平台文件列表",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.FILE_READ.mark))],
)
@app_scope(OpenApiScopeCode.FILE_READ)
def list_files(
    request: Request,
    folder: str | None = Query(default=None, description="存储目录过滤"),
    keyword: str | None = Query(default=None, description="关键字（文件名）"),
    page: int = Query(default=1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页记录数"),
    app: CurrentApp = Depends(get_current_app),
    service: FileStorageService = Depends(get_file_service),
):
    """查询文件列表（需 `file:read` scope）。"""
    result = service.list_files(folder=folder, keyword=keyword, page=page, page_size=page_size)
    return success_response(result, request)


@router.post(
    "",
    summary="开放平台上传文件",
    response_model=ApiResponse[dict],
    status_code=201,
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.FILE_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.FILE_WRITE)
def upload_file(
    body: OpenFileUploadRequest,
    request: Request,
    app: CurrentApp = Depends(get_current_app),
    service: FileStorageService = Depends(get_file_service),
):
    """上传文件（需 `file:write` scope；内容 base64 内嵌 JSON body）。"""
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationException(message="content_base64 不是合法的 Base64 编码") from exc
    if not data:
        raise ValidationException(message="文件内容为空")
    result = service.save_bytes(
        data=data,
        filename=body.filename,
        folder=body.folder,
        operator=get_app_operator_context(app),
        app_owner=app.app_id,
    )
    return success_response(result, request, code=201)


@router.get(
    "/{file_path:path}",
    summary="开放平台获取文件",
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.FILE_READ.mark))],
)
@app_scope(OpenApiScopeCode.FILE_READ)
def get_file(
    file_path: str = Path(description="文件路径（存储 key 或相对路径）"),
    request: Request = ...,
    app: CurrentApp = Depends(get_current_app),
    service: FileStorageService = Depends(get_file_service),
):
    """下载文件（需 `file:read` scope；本地存储返回文件流，云存储返回 302 重定向 URL）。"""
    result = service.download_file(file_path, operator=get_app_operator_context(app))
    return result


@router.delete(
    "/{file_id}",
    summary="开放平台删除文件",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_app_scope(OpenApiScopeCode.FILE_WRITE.mark))],
)
@app_scope(OpenApiScopeCode.FILE_WRITE)
def delete_file(
    file_id: int = Path(ge=1, description="文件 ID"),
    request: Request = ...,
    app: CurrentApp = Depends(get_current_app),
    service: FileStorageService = Depends(get_file_service),
):
    """软删除文件（需 `file:write` scope）。"""
    service.delete_file(file_id, operator=get_app_operator_context(app))
    return success_response({"deleted": True}, request)
