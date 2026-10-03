#!/usr/bin/env python3
"""开放接口（网关）业务逻辑。

本模块承载开放接口域（/api/open/v1，供外部应用调用汉江平台能力）的核心逻辑：
1. 应用身份鉴权（authenticate）：X-App-Id/X-App-Key 明文比对 或 HanJiang-1 签名校验，
   并强制审批门槛（approval_status 非 approved 一律拒绝）；
2. HanJiang-1 协议函数：签名串拼装、签名重算校验、HTTP 日期解析、URI 提取。

与门户服务（src/services/open_portal/）严格区分：
- 本域服务面向"应用调用开放接口"的协议层；
- 门户服务面向"开发者登录开放平台门户"的业务层；
- 应用数据（openapi_apps）的管理端 CRUD/审批在 src/services/admin/openapi_app_service.py。
通用加密原语（SHA256、Fernet、HMAC）在 src/utils/security.py，
公共工具（generate_app_id / parse_scopes / scope 目录映射）在 src/utils/openapi_utils.py。
"""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from fastapi import Request

from src.constants.constants import (
    OPENAPI_ALGORITHM,
    OPENAPI_CONTENT_TYPE,
    OPENAPI_HEADER_APP_ID,
    OPENAPI_HEADER_APP_KEY,
    OPENAPI_HEADER_AUTHORIZATION,
    OPENAPI_HEADER_DATE,
    OPENAPI_SIGNATURE_WINDOW_SECONDS,
)
from src.constants.enums import AppApprovalStatus, AppAuthMode, AppStatus
from src.core.exceptions import AuthenticationException, AuthorizationException
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.openapi_app import CurrentApp
from src.utils import security
from src.utils.openapi_utils import parse_scopes


def build_signing_string(
    *,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
) -> str:
    """构造 HanJiang-1 待签名串（与外部调用方的协议约定，勿随意改）。
    格式：Ver + METHOD + URI + Content-Type + Date + SHA256(body)
    直接拼接，无分隔符。
    注意：Content-Type 固定为 application/json（与请求是否携带 body 无关），
    GET 无 body 时同样拼接该固定值，body 为空则 SHA256(body) 取空字符串。
    """
    body_hash = security.sha256_hex(body.decode("utf-8")) if body else ""
    return "".join(
        [
            OPENAPI_ALGORITHM,
            method.upper(),
            uri,
            content_type,
            date,
            body_hash,
        ]
    )


def verify_request_signature(
    *,
    app_key_plain: str,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
    signature: str,
) -> bool:
    """校验请求签名。"""
    expected = security.hmac_sha256_hex(
        app_key_plain,
        build_signing_string(method=method, uri=uri, content_type=content_type, date=date, body=body),
    )
    return security.constant_time_equals(expected, signature)


def _extract_uri(request: Request) -> str:
    """从请求中提取 URI（path + raw query，不含域名）。"""
    uri = request.url.path
    if request.url.query:
        uri += f"?{request.url.query}"
    return uri


def _parse_http_date(date_str: str) -> datetime | None:
    """解析 HTTP 标准格式日期，如 'Wed, 23 Jan 2013 06:43:08 GMT'。"""
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (TypeError, ValueError):
        return None


class OpenGatewayService:
    """开放接口网关鉴权服务（每请求调用，仅做身份与审批校验，不触碰业务数据）。"""

    def __init__(self, repo: OpenApiAppRepository) -> None:
        self._repository = repo

    async def authenticate(self, request: Request) -> CurrentApp:
        """解析开放平台应用身份。
        鉴权流程：
            1. 应用存在且启用（status=active）；
            2. 审批状态须为 approved（pending/rejected 一律拒绝——申请-审批闭环的强制门槛）；
            3. 按 app.auth_mode 分流：
               - plain：仅接受 X-App-Key 明文比对 SHA256；
               - hmac：  仅接受 HanJiang-1 签名（时间窗 + 重算签名）；
               - both：  两种都接受（灰度期）。
        """
        app_id = request.headers.get(OPENAPI_HEADER_APP_ID)
        if not app_id:
            raise AuthenticationException(message="缺少请求头 X-App-Id")
        app = self._repository.get_by_app_id(app_id)
        if app is None or app.status != AppStatus.ACTIVE.value:
            raise AuthenticationException(message="App 无效或已停用")
        # 审批门槛：仅放行已通过审批的应用（开发者自助应用需管理端审批通过后方可调用）
        if app.approval_status != AppApprovalStatus.APPROVED.value:
            raise AuthorizationException(
                message=f"应用 {app.app_id} 未通过审批（当前状态：{app.approval_status}），请联系管理员"
            )
        try:
            mode = AppAuthMode(app.auth_mode or AppAuthMode.PLAIN.value)
        except ValueError:
            mode = AppAuthMode.PLAIN
        plain_key = request.headers.get(OPENAPI_HEADER_APP_KEY)
        authorization = request.headers.get(OPENAPI_HEADER_AUTHORIZATION, "")
        date = request.headers.get(OPENAPI_HEADER_DATE, "")
        authenticated = False
        # 分支 1：明文 AppKey 校验
        if mode in (AppAuthMode.PLAIN, AppAuthMode.BOTH) and plain_key:
            authenticated = security.constant_time_equals(security.sha256_hex(plain_key), app.app_key_hash)
        # 分支 2：HanJiang-1 签名校验
        if not authenticated and mode in (AppAuthMode.HMAC, AppAuthMode.BOTH) and authorization:
            authenticated = await self._verify_hmac_signature(
                request=request,
                app_encrypted=app.app_key_encrypted,
                date=date,
                authorization=authorization,
            )
        if not authenticated:
            raise AuthenticationException(message="应用鉴权失败")
        # 更新 last_used_at（失败不阻断主流程）
        try:
            self._repository.touch_last_used(app_id)
        except Exception:
            self._repository.rollback()
        return CurrentApp(
            app_id=app.app_id,
            name=app.name,
            description=app.description,
            scopes=parse_scopes(app.scopes),
            auth_mode=mode.value,
            rate_limit_per_minute=app.rate_limit_per_minute,
        )

    async def _verify_hmac_signature(
        self,
        *,
        request: Request,
        app_encrypted: str | None,
        date: str,
        authorization: str,
    ) -> bool:
        """HanJiang-1 签名校验：时间窗 + 解密 secret + 重算签名。"""
        # 1. 时间窗：解析 HTTP Date 格式
        if not date:
            return False
        request_time = _parse_http_date(date)
        if request_time is None:
            return False
        now = datetime.now(UTC)
        if abs((now - request_time).total_seconds()) > OPENAPI_SIGNATURE_WINDOW_SECONDS:
            return False
        # 2. 解密取回明文 secret
        secret = security.decrypt_text(app_encrypted)
        if not secret:
            return False
        # 3. 提取 Authorization 中的签名值
        # 格式：HanJiang-1 {app_id}:{signature}
        parts = authorization.split(":", 1)
        if len(parts) != 2 or not parts[1]:
            return False
        signature = parts[1].strip()
        # 4. 取请求体
        body = b""
        try:
            body = await request.body()
        except Exception:
            body = b""
        # 5. Content-Type（协议固定为 application/json，不从请求头取值）
        content_type = OPENAPI_CONTENT_TYPE
        # 6. 重算签名并比对
        return verify_request_signature(
            app_key_plain=secret,
            method=request.method,
            uri=_extract_uri(request),
            content_type=content_type,
            date=date,
            body=body,
            signature=signature,
        )
