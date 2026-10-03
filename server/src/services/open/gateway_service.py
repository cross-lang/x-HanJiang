#!/usr/bin/env python3
"""开放接口（网关）业务逻辑。

本模块承载开放接口域（/api/open/v1，供外部应用调用汉江平台能力）的核心逻辑：
1. 应用身份鉴权（authenticate）：X-App-Id/X-App-Key 明文比对 或 HanJiang-1 签名校验，
   并强制审批门槛（approval_status 非 approved 一律拒绝）；
2. 签名 / 解签协议纯函数已下沉至 src/core/signature.py；
   FastAPI Request 由 API 层（dependencies.get_current_app）转换为
   OpenApiAuthContext 纯数据后传入，本层不依赖 Web 框架对象。

与门户服务（src/services/open_portal/）严格区分：
- 本域服务面向"应用调用开放接口"的协议层；
- 门户服务面向"开发者登录开放平台门户"的业务层；
- 应用数据（openapi_apps）的管理端 CRUD/审批在 src/services/admin/openapi_app_service.py。
通用加密原语（SHA256、Fernet、HMAC）在 src/utils/security.py，
公共工具（generate_app_id / parse_scopes / scope 目录映射）在 src/utils/openapi_utils.py。
"""

from src.constants.constants import OPENAPI_CONTENT_TYPE
from src.constants.enums import AppApprovalStatus, AppAuthMode, AppStatus
from src.core import signature
from src.core.exceptions import AuthenticationException, AuthorizationException
from src.repositories.openapi_app_repository import OpenApiAppRepository
from src.schemas.open.app import CurrentApp
from src.schemas.open.request_context import OpenApiAuthContext
from src.utils import security
from src.utils.openapi_utils import parse_scopes


class OpenGatewayService:
    """开放接口网关鉴权服务（每请求调用，仅做身份与审批校验，不触碰业务数据）。"""

    def __init__(self, repo: OpenApiAppRepository) -> None:
        self._repository = repo

    async def authenticate(self, ctx: OpenApiAuthContext) -> CurrentApp:
        """解析开放平台应用身份。

        鉴权流程：
            1. 应用存在且启用（status=active）；
            2. 审批状态须为 approved（pending/rejected 一律拒绝——申请-审批闭环的强制门槛）；
            3. 按 app.auth_mode 分流：
               - plain：仅接受 X-App-Key 明文比对 SHA256；
               - hmac：  仅接受 HanJiang-1 签名（时间窗 + 重算签名）；
               - both：  两种都接受（灰度期）。

        Args:
            ctx: API 层从 FastAPI Request 剥离的鉴权上下文（纯数据，见
                src.schemas.open.request_context.OpenApiAuthContext）。
        """
        if not ctx.app_id:
            raise AuthenticationException(message="缺少请求头 X-App-Id")
        app = self._repository.get_by_app_id(ctx.app_id)
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
        authenticated = False
        # 分支 1：明文 AppKey 校验
        if mode in (AppAuthMode.PLAIN, AppAuthMode.BOTH) and ctx.plain_key:
            authenticated = security.constant_time_equals(security.sha256_hex(ctx.plain_key), app.app_key_hash)
        # 分支 2：HanJiang-1 签名校验（签名/解签协议函数见 src/core/signature.py）
        if not authenticated and mode in (AppAuthMode.HMAC, AppAuthMode.BOTH) and ctx.authorization:
            authenticated = self._verify_hmac_signature(app_encrypted=app.app_key_encrypted, ctx=ctx)
        if not authenticated:
            raise AuthenticationException(message="应用鉴权失败")
        # 更新 last_used_at（失败不阻断主流程）
        try:
            self._repository.touch_last_used(app.app_id)
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

    def _verify_hmac_signature(self, *, app_encrypted: str | None, ctx: OpenApiAuthContext) -> bool:
        """HanJiang-1 签名解签：时间窗 + 解密 secret + 调用 core.signature 重算比对。

        本方法只做鉴权编排；协议计算全部委托 src/core/signature.py。
        """
        # 1. 时间窗：X-App-Date 缺失或超窗一律拒绝
        if not ctx.date or not signature.is_request_date_valid(ctx.date):
            return False
        # 2. 解密取回明文 secret
        secret = security.decrypt_text(app_encrypted)
        if not secret:
            return False
        # 3. 提取 Authorization 中的签名值
        # 格式：HanJiang-1 {app_id}:{signature}
        parts = ctx.authorization.split(":", 1)
        if len(parts) != 2 or not parts[1]:
            return False
        # 4. 解签：重算签名并常量时间比对（协议 Content-Type 固定 application/json）
        return signature.verify_signature(
            app_key=secret,
            method=ctx.method,
            uri=ctx.uri,
            content_type=OPENAPI_CONTENT_TYPE,
            date=ctx.date,
            body=ctx.body,
            signature=parts[1].strip(),
        )
