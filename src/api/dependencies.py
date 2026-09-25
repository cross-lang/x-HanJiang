#!/usr/bin/env python3
"""
FastAPI 依赖注入模块

本模块定义了 API 层通用的 FastAPI Depends 依赖项工厂函数，
用于在路由处理函数中通过参数注入公共依赖。

Functions:
    get_request_id: 获取当前请求 ID
    get_pagination: 获取分页参数
    get_db_session: 获取数据库会话（FastAPI 依赖）
    get_user_service: 获取用户服务实例
"""

from collections.abc import Generator
from functools import lru_cache
from time import time

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.exceptions import AuthorizationException
from src.infras.database import get_cached_database_provider
from src.schemas.auth import CurrentUserResponse
from src.schemas.common import PaginatedRequest
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.services.file_service import FileStorageService
from src.services.maintenance_service import MaintenanceService
from src.services.notification_service import NotificationService
from src.services.permission_service import PermissionService
from src.utils.helpers import get_client_ip

# HTTP Bearer 认证方案（auto_error=False，缺失令牌时由 get_current_user 统一抛 401）
_bearer_scheme = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str | None:
    """从请求状态中获取当前请求 ID。"""
    return getattr(request.state, "request_id", None)


def get_pagination(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedRequest:
    """获取分页参数。"""
    return PaginatedRequest(page=page, page_size=page_size)


def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话（FastAPI 依赖）。

    使用 FastAPI 的依赖注入机制管理数据库会话生命周期。
    确保每个请求都有独立的会话，并在请求结束后自动关闭。

    Yields:
        Session: 数据库会话对象
    """
    session_factory = get_cached_database_provider().get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_notification_dispatcher(
    db_session: Session = Depends(get_db_session),
) -> "NotificationDispatcher":
    """获取通知调度器实例（供 AlertService 等内部服务使用）。"""
    from src.infras.notification import get_registry
    from src.notification.dispatcher import NotificationDispatcher

    return NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )


def get_notification_service(
    db_session: Session = Depends(get_db_session),
) -> NotificationService:
    """获取通知业务服务实例。"""
    from src.infras.notification import get_registry
    from src.notification.dispatcher import NotificationDispatcher

    dispatcher = NotificationDispatcher(
        registry=get_registry(),
        session=db_session,
    )
    return NotificationService(
        dispatcher=dispatcher,
        session=db_session,
    )


def get_user_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取用户仓库实例（可被 DI 容器覆盖）。"""
    from src.repositories.user_repository import UserRepository

    return UserRepository(session=db_session)


def get_login_log_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取登录日志仓库实例。"""
    from src.repositories.login_log_repository import LoginLogRepository

    return LoginLogRepository(session=db_session)


def get_user_service(
    user_repository=Depends(get_user_repository),
    dispatcher: "NotificationDispatcher" = Depends(get_notification_dispatcher),
):
    """使用当前请求的 Repository 创建用户服务。"""
    from src.services.user_service import UserService

    return UserService(user_repository=user_repository, dispatcher=dispatcher)


def get_alert_service(
    dispatcher: "NotificationDispatcher" = Depends(get_notification_dispatcher),
    db_session: Session = Depends(get_db_session),
) -> AlertService:
    """获取告警服务实例。"""
    return AlertService(dispatcher=dispatcher, session=db_session)


def get_audit_service(
    db_session: Session = Depends(get_db_session),
) -> AuditService:
    """获取审计服务。"""
    from src.repositories.audit_log_repository import AuditLogRepository

    return AuditService(audit_log_repository=AuditLogRepository(session=db_session))


@lru_cache(maxsize=1)
def get_file_service() -> FileStorageService:
    """获取共享的文件存储服务，使用 StorageProvider 抽象层。"""
    from src.infras.storage import get_cached_storage_provider

    return FileStorageService(provider=get_cached_storage_provider())


def get_auth_service(
    user_repository=Depends(get_user_repository),
    login_log_repository=Depends(get_login_log_repository),
    dispatcher: "NotificationDispatcher" = Depends(get_notification_dispatcher),
):
    """获取认证服务。"""
    return AuthService(
        user_repository=user_repository,
        login_log_repository=login_log_repository,
        dispatcher=dispatcher,
    )


def get_role_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取角色仓库实例。"""
    from src.repositories.role_repository import RoleRepository

    return RoleRepository(session=db_session)


def get_permission_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取权限仓库实例。"""
    from src.repositories.permission_repository import PermissionRepository

    return PermissionRepository(session=db_session)


def get_role_permission_repository(
    db_session: Session = Depends(get_db_session),
):
    """获取角色权限关联仓库实例。"""
    from src.repositories.role_permission_repository import RolePermissionRepository

    return RolePermissionRepository(session=db_session)


def get_role_service(
    role_repository=Depends(get_role_repository),
    role_permission_repository=Depends(get_role_permission_repository),
    permission_repository=Depends(get_permission_repository),
):
    """使用当前请求的 Repository 创建角色服务。"""
    from src.services.role_service import RoleService

    return RoleService(
        role_repository=role_repository,
        role_permission_repository=role_permission_repository,
        permission_repository=permission_repository,
    )


def get_permission_service(
    permission_repository=Depends(get_permission_repository),
    role_permission_repository=Depends(get_role_permission_repository),
    role_repository=Depends(get_role_repository),
    dispatcher: "NotificationDispatcher" = Depends(get_notification_dispatcher),
):
    """使用当前请求的 Repository 创建权限服务。"""
    from src.services.permission_service import PermissionService

    return PermissionService(
        permission_repository=permission_repository,
        role_permission_repository=role_permission_repository,
        role_repository=role_repository,
        dispatcher=dispatcher,
    )


def get_login_log_service(
    login_log_repository=Depends(get_login_log_repository),
):
    """使用当前请求的 Repository 创建登录日志服务。"""
    from src.services.login_log_service import LoginLogService

    return LoginLogService(login_log_repository=login_log_repository)


def get_openapi_app_service(
    db_session: Session = Depends(get_db_session),
):
    """创建开放平台应用管理服务。"""
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.services.openapi_app_service import OpenApiAppService

    return OpenApiAppService(repo=OpenApiAppRepository(session=db_session))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUserResponse:
    """解析 Bearer 令牌，返回当前登录用户.

    使用 HTTPBearer 认证方案，Swagger UI 会自动在右上角显示 Authorize 按钮，
    并为所有依赖本函数的接口标注锁图标；点 Authorize 填一次令牌即可全局生效。
    """
    token = credentials.credentials if credentials is not None else None
    return auth_service.get_current_user(token)


def require_role(role_code: str):
    """要求当前用户必须属于指定角色。"""

    def dependency(
        current_user: CurrentUserResponse = Depends(get_current_user),
    ) -> CurrentUserResponse:
        if current_user.role_code != role_code and current_user.role_code != "super_admin":
            raise AuthorizationException(message=f"需要角色 {role_code}")
        return current_user

    return dependency


def require_permission(permission_code: str):
    """要求当前用户必须拥有指定权限。权限结果按角色缓存。"""

    def dependency(
        current_user: CurrentUserResponse = Depends(get_current_user),
        permission_service: PermissionService = Depends(get_permission_service),
    ) -> CurrentUserResponse:
        if not permission_service.has_permission(current_user.id, permission_code):
            raise AuthorizationException(message=f"缺少权限: {permission_code}")
        return current_user

    return dependency


def get_operator_context(
    current_user: CurrentUserResponse | None = None,
) -> dict[str, object]:
    """构造操作人上下文（供写操作审计/日志使用）。

    当前未启用强制鉴权，current_user 可能为 None，返回最小上下文。
    """
    if current_user is None:
        return {"operator_id": None, "operator_name": None}
    return {
        "operator_id": current_user.id,
        "operator_name": current_user.username,
    }


# ============================================================
# 面向应用（开放平台）鉴权
# ============================================================


class CurrentApp(BaseModel):
    """当前调用方应用（机器身份，无终端用户上下文）。"""

    app_id: str
    name: str
    scopes: list[str]
    auth_mode: str
    rate_limit_per_minute: int


async def get_current_app(
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> CurrentApp:
    """解析开放平台应用身份（X-App-Id / X-App-Key 或 HMAC 签名头）。

    与 get_current_user 平行，互不影响。鉴权逻辑按 app.auth_mode 分流：
        - plain：仅接受 X-App-Key 明文比对 SHA256；
        - hmac：  仅接受 HMAC 签名（时间窗 + nonce 去重 + 重算签名）；
        - both：  两种都接受（灰度期）。
    """
    from src.core.exceptions import AuthenticationException
    from src.repositories.openapi_app_repository import OpenApiAppRepository
    from src.utils import app_auth

    app_id = request.headers.get(OPENAPI_HEADER_APP_ID)
    if not app_id:
        raise AuthenticationException(message="缺少请求头 X-App-Id")

    repo = OpenApiAppRepository(session=db_session)
    app = repo.get_by_app_id(app_id)
    if app is None or app.status != "active":
        raise AuthenticationException(message="App 无效或已停用")

    try:
        mode = AppAuthMode(app.auth_mode or AppAuthMode.PLAIN.value)
    except ValueError:
        mode = AppAuthMode.PLAIN
    plain_key = request.headers.get(OPENAPI_HEADER_APP_KEY)
    signature = request.headers.get(OPENAPI_HEADER_SIGNATURE)
    timestamp = request.headers.get(OPENAPI_HEADER_TIMESTAMP, "")
    nonce = request.headers.get(OPENAPI_HEADER_NONCE, "")

    authenticated = False

    # ── 分支 1：明文 AppKey 校验 ──
    if mode in (AppAuthMode.PLAIN, AppAuthMode.BOTH) and plain_key:
        authenticated = security.constant_time_equals(security.sha256_hex(plain_key), app.app_key_hash)

    # ── 分支 2：HMAC 签名校验（预留分支，未来切 auth_mode=hmac 时即生效）──
    if (
        not authenticated
        and mode in (AppAuthMode.HMAC, AppAuthMode.BOTH)
        and signature
    ):
        authenticated = await _verify_hmac_signature(
            request=request,
            app_encrypted=app.app_key_encrypted,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        )

    if not authenticated:
        raise AuthenticationException(message="应用鉴权失败")

    # 异步更新 last_used_at（失败不阻断）
    try:
        repo.touch_last_used(app_id)
    except Exception:
        db_session.rollback()

    current = CurrentApp(
        app_id=app.app_id,
        name=app.name,
        scopes=parse_scopes(app.scopes),
        auth_mode=mode,
        rate_limit_per_minute=app.rate_limit_per_minute,
    )
    request.state.current_app = current
    return current


async def _verify_hmac_signature(
    *,
    request: Request,
    app_encrypted: str | None,
    timestamp: str,
    nonce: str,
    signature: str,
) -> bool:
    """HMAC 签名校验：时间窗 + 解密 secret + 重算签名 + Redis nonce 去重。

    当前默认 auth_mode=plain，此分支不会被走到；代码已就绪，未来切 hmac 即可。
    """
    from src.utils import app_auth

    # 1. 时间窗
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time() - ts) > HMAC_TIMESTAMP_WINDOW_SECONDS:
        return False

    # 2. 解密取回明文 secret
    secret = security.decrypt_text(app_encrypted)
    if not secret:
        return False

    # 3. 重算签名（FastAPI 缓存 body，可重复读）
    body = b""
    try:
        body = await request.body()  # type: ignore[assignment]
    except Exception:
        body = b""

    if not verify_request_signature(
        app_key_plain=secret,
        method=request.method,
        url=str(request.url),
        body=body,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
    ):
        return False

    # 4. nonce 去重（Redis，失败降级为不拦截，避免开发环境无 Redis 时阻断）
    _try_nonce_dedup(OPENAPI_HEADER_NONCE, app_id=request.headers.get(OPENAPI_HEADER_APP_ID, ""), nonce=nonce)
    return True


def _try_nonce_dedup(header_name: str, *, app_id: str, nonce: str) -> None:
    """在 Redis 里 SETNX nonce，TTL = 时间窗。已存在说明重放，调用方应视为失败。

    当前 HMAC 未启用，本函数实际不会被调用；这里只做最小骨架，未来接 Redis provider 时完善。
    """
    # TODO: 接入 src/infras/cache.py，SETNX f"openapi:nonce:{app_id}:{nonce}" EX 300
    return None


def require_app_scope(scope: str):
    """要求当前应用必须拥有指定 scope。"""

    def dependency(app: CurrentApp = Depends(get_current_app)) -> CurrentApp:
        if scope not in app.scopes:
            from src.core.exceptions import AuthorizationException

            raise AuthorizationException(message=f"应用缺少 scope: {scope}")
        return app

    return dependency



