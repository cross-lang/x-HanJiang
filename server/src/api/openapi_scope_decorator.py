#!/usr/bin/env python3
"""开放平台 scope 装饰器。
用法：
    @router.get("/users", dependencies=[Depends(require_app_scope("user:read"))])
    @app_scope("user:read", "读取用户列表", "user", "read")
    async def list_users():
        ...
启动时自动扫描开放平台路由的 _scope_code 属性，upsert 到 openapi_scopes 表。
"""

from collections.abc import Callable

from src.core.logger import logger


def app_scope(code: str, name: str = "", module: str = "", operation: str = ""):
    """声明开放平台路由所需 scope（仅挂载元数据，鉴权仍用 Depends(require_app_scope(...))）。

    Args:
        code: scope 编码，如 user:read
        name: scope 中文名，如 读取用户列表
        module: 模块名，如 user
        operation: 操作类型，如 read
    """

    def decorator(func: Callable):
        func._scope_code = code
        func._scope_name = name
        func._scope_module = module
        func._scope_operation = operation
        return func

    return decorator


def collect_scopes_from_app(app) -> list[dict]:
    """扫描 FastAPI 应用所有路由，收集带 @app_scope 装饰器的 scope 元数据。"""
    scopes = []
    for route in app.routes:
        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            path = getattr(route, "path", "?")
            if hasattr(endpoint, "_scope_code"):
                logger.debug(f"Found app scope: {endpoint._scope_code} at {path}")
                scopes.append(
                    {
                        "scope_code": endpoint._scope_code,
                        "scope_name": endpoint._scope_name or endpoint._scope_code,
                        "module": endpoint._scope_module or "",
                        "operation": endpoint._scope_operation or "",
                        "description": (endpoint.__doc__ or "")[:250],
                    }
                )
    # 按 scope_code 去重
    seen = set()
    unique = []
    for s in scopes:
        if s["scope_code"] not in seen:
            seen.add(s["scope_code"])
            unique.append(s)
    return unique


def sync_scopes_to_db(app) -> tuple[int, int]:
    """启动时将开放平台路由上的 @app_scope 声明对账同步到 openapi_scopes 表。

    以代码中的 scope 声明为唯一事实来源：
      - 代码中存在、表中已存在 → 按最新元数据更新并取消废弃标记；
      - 代码中存在、表中不存在 → 新增；
      - 表中存在、代码中已不存在 → 标记 is_deprecated=True（不物理删除）。
    sort_order 按扫描顺序从 1 递增；description 截断至 250 字。
    任一步骤失败由 session 上下文自动回滚并向上抛出，由调用方决定是否阻断启动。

    Args:
        app: FastAPI 应用实例

    Returns:
        (active_count, deprecated_count): 本次启用 scope 数与新标记废弃数
    """
    from src.infras.database import get_cached_database_provider
    from src.models.entities.app_entity import OpenApiScopeEntity

    collected_scopes = collect_scopes_from_app(app)
    logger.debug(f"Collected scopes: {[s['scope_code'] for s in collected_scopes]}")
    active_scope_codes = {s["scope_code"] for s in collected_scopes}

    with get_cached_database_provider().session() as scope_session:
        for idx, sc in enumerate(collected_scopes, start=1):
            existing = scope_session.query(OpenApiScopeEntity).filter_by(scope_code=sc["scope_code"]).first()
            if existing:
                existing.scope_name = sc["scope_name"]
                existing.module = sc["module"]
                existing.operation = sc["operation"]
                if sc["description"]:
                    existing.description = (sc["description"] or "")[:250]
                existing.sort_order = idx
                existing.is_deprecated = False
            else:
                payload = dict(sc)
                payload["description"] = (payload.get("description") or "")[:250]
                payload["sort_order"] = idx
                scope_session.add(OpenApiScopeEntity(**payload, is_deprecated=False))

        deprecated_scopes = (
            scope_session.query(OpenApiScopeEntity)
            .filter(
                OpenApiScopeEntity.is_deprecated.is_(False),
                ~OpenApiScopeEntity.scope_code.in_(active_scope_codes),
            )
            .all()
        )
        for d in deprecated_scopes:
            d.is_deprecated = True
            logger.info(f"Scope deprecated (not found in routes): {d.scope_code}")

    logger.info(
        f"OpenAPI scopes auto-synced: {len(collected_scopes)} active, "
        f"{len(deprecated_scopes)} deprecated"
    )
    return len(collected_scopes), len(deprecated_scopes)
