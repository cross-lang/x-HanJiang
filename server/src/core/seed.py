#!/usr/bin/env python3
"""
种子数据管理模块
应用启动时检测并自动创建系统内置种子数据：
    1. 超级管理员角色（roles 表，role_type=system，role_code=SUPERADMIN）
    2. 超级管理员用户（users 表，username=superadmin，绑定上述角色）
    3. 内置权限（permissions 表）
    4. 角色权限关联（role_permissions 表，将全部权限绑定到超级管理员角色）
若数据已存在则跳过，保证幂等。

Functions:
    init_seed_data: 初始化种子数据（幂等）
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.constants import (
    SUPERADMIN_EMAIL,
    SUPERADMIN_NAME,
    SUPERADMIN_PASSWORD,
    SUPERADMIN_USERNAME,
)
from src.constants.enums import SystemRoleCode
from src.constants.permissions import PERMISSION_CATALOG, PermissionCode
from src.core.logger import logger
from src.infras.database import acquire_mysql_lock, get_cached_database_provider, release_mysql_lock
from src.models.entities.menu_entity import MenuEntity
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
    UserEntity,
    UserRoleEntity,
)
from src.utils.security import hash_password

# ── 内置权限定义 ──────────────────────────────────────────────
# 权限元数据唯一事实来源为 src.constants.permissions.PermissionCode，
# 不再在种子模块维护副本；PERMISSION_CATALOG 按定义顺序（sort_order）遍历。

# ── 内置菜单定义 ──────────────────────────────────────────────
# (parent_title 或 0, title, path, icon, perm_code, sort_order, type)
# parent 为 0 表示根菜单
_SEED_MENUS = [
    # 根菜单
    (0, "首页", "/home", "Odometer", PermissionCode.HOME_VIEW.mark, 1, "menu"),
    (0, "仪表盘", "/dashboard", "DataAnalysis", PermissionCode.DASHBOARD_VIEW.mark, 2, "menu"),
    (0, "系统管理", "/system", "Setting", None, 3, "directory"),
    # 系统管理子菜单
    ("系统管理", "用户管理", "/users", "User", PermissionCode.USER_VIEW.mark, 1, "menu"),
    ("系统管理", "角色管理", "/roles", "UserFilled", PermissionCode.ROLE_VIEW.mark, 2, "menu"),
    ("系统管理", "权限管理", "/permissions", "Lock", PermissionCode.PERMISSION_VIEW.mark, 3, "menu"),
    ("系统管理", "文件管理", "/files", "Folder", PermissionCode.FILE_VIEW.mark, 4, "menu"),
    ("系统管理", "通知管理", "/system-notification", "Bell", PermissionCode.NOTIFICATION_CONFIG.mark, 5, "menu"),
    ("系统管理", "公告管理", "/announcements", "Tickets", PermissionCode.ANNOUNCEMENT_VIEW.mark, 6, "menu"),
    ("系统管理", "审计日志", "/logs/audit", "Document", PermissionCode.AUDIT_LOG_VIEW.mark, 7, "menu"),
    ("系统管理", "登录日志", "/logs/login", "User", PermissionCode.LOGIN_LOG_VIEW.mark, 8, "menu"),
    ("系统管理", "站内信", "/station-messages", "Message", PermissionCode.STATION_VIEW.mark, 9, "menu"),
    # 接口管理
    (0, "接口管理", "/apis", "Link", None, 4, "directory"),
    ("接口管理", "Swagger文档", "/apis/swagger", "Document", PermissionCode.SWAGGER_VIEW.mark, 1, "menu"),
    # 开放平台
    (0, "开放平台", "/open", "Connection", None, 5, "directory"),
    ("开放平台", "应用管理", "/apps", "Grid", PermissionCode.OPENAPI_APP_VIEW.mark, 1, "menu"),
    ("开放平台", "应用审批", "/app-approvals", "Stamp", PermissionCode.OPENAPI_APP_APPROVE.mark, 2, "menu"),
    ("开放平台", "权限管理", "/app-scopes", "Lock", PermissionCode.OPENAPI_APP_VIEW.mark, 3, "menu"),
    ("开放平台", "开发者管理", "/open-developers", "Avatar", PermissionCode.OPENAPI_DEV_VIEW.mark, 4, "menu"),
    # 个人中心（一级菜单，参考开放平台门户样式）
    (0, "个人中心", "/profile", "User", PermissionCode.PROFILE_VIEW.mark, 6, "menu"),
]


def init_seed_data() -> None:
    """初始化系统种子数据（幂等，可重复调用）。

    使用 MySQL 命名锁串行化：gunicorn 多 worker 并发执行 lifespan 时，
    仅允许一个 worker 运行种子初始化，避免权限唯一键并发插入竞态（1062）。
    """
    session = get_cached_database_provider().get_session_factory()()
    try:
        if not acquire_mysql_lock(session, "hanjiang.seed", timeout=60):
            logger.warning("Seed data initialization skipped: failed to acquire seed lock")
            return
        # 1. 权限（元数据全部来自 PermissionCode 统一目录）
        perm_map: dict[str, PermissionEntity] = {}
        for perm_def in PERMISSION_CATALOG:
            code = perm_def.mark
            perm = session.execute(select(PermissionEntity).where(PermissionEntity.perm_code == code)).scalars().first()
            if perm is None:
                perm = PermissionEntity(
                    perm_code=code,
                    perm_name=perm_def.perm_name,
                    module=perm_def.module,
                    operation=perm_def.operation,
                    description=perm_def.description,
                    sort_order=perm_def.sort_order,
                )
                session.add(perm)
                session.flush()
                logger.info(f"Seed permission created: perm_code={code}")
            perm_map[code] = perm
        # 2. 超级管理员角色
        role = _find_role_by_code(session, SystemRoleCode.SUPERADMIN.mark)
        if role is None:
            role = RoleEntity(
                role_name=SystemRoleCode.SUPERADMIN.desc,
                role_code=SystemRoleCode.SUPERADMIN.mark,
                description="系统内置超级管理员角色，拥有全部权限",
                role_type="system",
                status="enabled",
            )
            session.add(role)
            session.flush()
            logger.info(f"Seed role created: role_code={SystemRoleCode.SUPERADMIN.mark}")
        # 3. 超级管理员角色 → 绑定全部权限
        for perm in perm_map.values():
            _ensure_role_permission(session, role.id, perm.id)
        # 3.5 管理员角色（除不能管理超级管理员外，其余权限相同）
        admin_role = _find_role_by_code(session, SystemRoleCode.ADMIN.mark)
        if admin_role is None:
            admin_role = RoleEntity(
                role_name=SystemRoleCode.ADMIN.desc,
                role_code=SystemRoleCode.ADMIN.mark,
                description="系统内置管理员角色，拥有除超级管理员管理外的全部权限",
                role_type="system",
                status="enabled",
            )
            session.add(admin_role)
            session.flush()
            logger.info(f"Seed role created: role_code={SystemRoleCode.ADMIN.mark}")
        # 管理员角色 → 绑定全部权限（幂等，无论角色是否新建都执行）
        for perm in perm_map.values():
            _ensure_role_permission(session, admin_role.id, perm.id)
        # 3.6 普通用户角色（绑定个人基础功能权限，无管理权限）
        user_role = _find_role_by_code(session, SystemRoleCode.USER.mark)
        if user_role is None:
            user_role = RoleEntity(
                role_name=SystemRoleCode.USER.desc,
                role_code=SystemRoleCode.USER.mark,
                description="系统内置普通用户角色，可查看首页，并可访问个人中心、站内信与全局搜索等基础功能",
                role_type="system",
                status="enabled",
            )
            session.add(user_role)
            session.flush()
            logger.info(f"Seed role created: role_code={SystemRoleCode.USER.mark}")
        # 3.7 普通用户角色 → 绑定个人基础功能权限（幂等）
        user_basic_codes = [
            PermissionCode.HOME_VIEW.mark,
            PermissionCode.PROFILE_VIEW.mark,
            PermissionCode.PROFILE_EDIT.mark,
            PermissionCode.PROFILE_PASSWORD.mark,
            PermissionCode.PROFILE_EMAIL.mark,
            PermissionCode.PROFILE_PHONE.mark,
            PermissionCode.STATION_VIEW.mark,
            PermissionCode.STATION_EDIT.mark,
            PermissionCode.SEARCH.mark,
        ]
        for code in user_basic_codes:
            target_perm = perm_map.get(code)
            if target_perm is not None:
                _ensure_role_permission(session, user_role.id, target_perm.id)
        # 4. 超级管理员用户
        admin = session.execute(select(UserEntity).where(UserEntity.username == SUPERADMIN_USERNAME)).scalars().first()
        if admin is None:
            from datetime import date

            admin = UserEntity(
                username=SUPERADMIN_USERNAME,
                name=SUPERADMIN_NAME,
                email=SUPERADMIN_EMAIL,
                password_hash=hash_password(SUPERADMIN_PASSWORD),
                phone="",
                gender="male",
                birthday=date(1970, 1, 1),
                avatar_url=None,
                status="enabled",
            )
            session.add(admin)
            session.flush()
            logger.info(f"Seed admin user created: username={SUPERADMIN_USERNAME}")
        # 4.5 幂等补绑：无论用户是新建还是旧库遗留，都必须确保绑定超级管理员角色
        _ensure_user_role(session, admin.id, role.id)
        # 5. 菜单数据
        _seed_menus(session)
        # 6. 通知渠道配置（把 .env 里的 SMTP 等配置初始化进数据库）
        _seed_notification_configs(session)
        session.commit()
        logger.info("Seed data initialization completed")
    except Exception as e:  # noqa: BLE001
        session.rollback()
        logger.warning(f"Seed data initialization skipped: {e}")
    finally:
        release_mysql_lock(session, "hanjiang.seed")
        session.close()


def _find_role_by_code(session: Session, role_code: str) -> RoleEntity | None:
    """按角色编码查询内置角色。"""
    return session.execute(select(RoleEntity).where(RoleEntity.role_code == role_code)).scalars().first()


def _ensure_role_permission(session: Session, role_id: int, permission_id: int) -> None:
    """确保角色权限关联存在，不存在则创建。"""
    relation = (
        session.execute(
            select(RolePermissionEntity).where(
                RolePermissionEntity.role_id == role_id,
                RolePermissionEntity.permission_id == permission_id,
            )
        )
        .scalars()
        .first()
    )
    if relation is None:
        relation = RolePermissionEntity(
            role_id=role_id,
            permission_id=permission_id,
        )
        session.add(relation)
        session.flush()


def _ensure_user_role(session: Session, user_id: int, role_id: int) -> None:
    """确保用户角色关联存在，不存在则创建（幂等）。

    兼容旧库：早期 users 表以 role_id 单列承载角色，新模型改为
    user_roles 多对多关联；对已存在的旧用户执行种子初始化时，
    必须显式补建关联，否则旧用户登录后无任何角色与权限。
    """
    relation = (
        session.execute(
            select(UserRoleEntity).where(
                UserRoleEntity.user_id == user_id,
                UserRoleEntity.role_id == role_id,
            )
        )
        .scalars()
        .first()
    )
    if relation is None:
        relation = UserRoleEntity(user_id=user_id, role_id=role_id)
        session.add(relation)
        session.flush()


def _seed_menus(session: Session) -> None:
    """初始化菜单数据（幂等）。

    幂等键为 ``(parent_id, title)``：菜单树中允许不同父级下存在同名菜单
    （如"系统管理/用户管理"与"开放平台/开发者管理"），仅按 title 判断会误跳过。

    同时执行一次兼容迁移：早期版本开放平台下该菜单名为"用户管理"，
    统一更名为"开发者管理"（按 父级+path 精确匹配，不影响系统管理下的用户管理）。
    """
    existing = session.execute(select(MenuEntity)).scalars().all()
    # 去重加固：同一父级下 (title, path) 完全相同的菜单仅保留 id 最小的一条。
    # 历史版本曾因"更名迁移 + _SEED_MENUS 新增同名条目"叠加产生重复记录
    # （如 开放平台/开发者管理 出现两条），幂等键无法发现，故在此显式清理。
    seen_key: dict[tuple[int, str, str], MenuEntity] = {}
    for m in sorted(existing, key=lambda x: x.id):
        key = (m.parent_id, m.title, m.path or "")
        if key in seen_key:
            session.delete(m)
            logger.info(f"Seed menu deduplicated: id={m.id} title={m.title} path={m.path}")
        else:
            seen_key[key] = m
    existing = session.execute(select(MenuEntity)).scalars().all()
    parent_map = {m.title: m for m in existing}
    openapi_parent = parent_map.get("开放平台")
    if openapi_parent is not None:
        for m in existing:
            if m.parent_id == openapi_parent.id and m.title == "用户管理" and m.path == "/open-developers":
                m.title = "开发者管理"
                logger.info("Seed menu renamed: 开放平台/用户管理 → 开发者管理")
    existing = session.execute(select(MenuEntity)).scalars().all()
    key_map = {(m.parent_id, m.title): m for m in existing}
    parent_map = {m.title: m for m in existing}
    for parent_title, title, path, icon, perm_code, sort_order, mtype in _SEED_MENUS:
        parent_id = 0
        if parent_title != 0:
            parent = parent_map.get(parent_title) if isinstance(parent_title, str) else None
            if parent:
                parent_id = parent.id
        if (parent_id, title) in key_map:
            continue
        m = MenuEntity(
            parent_id=parent_id,
            title=title,
            path=path,
            icon=icon,
            perm_code=perm_code,
            sort_order=sort_order,
            type=mtype,
            status="enabled",
        )
        session.add(m)
        session.flush()
        parent_map[title] = m
        key_map[(parent_id, title)] = m
        logger.info(f"Seed menu created: title={title}")


def _seed_notification_configs(session: Session) -> None:
    """初始化通知渠道配置（幂等）。
    把 .env / config.yaml 里已有的 SMTP 配置写入 system_notification_configs 表，
    这样管理后台就能看到并编辑；表已有记录则跳过。
    """
    from src.core.config import settings
    from src.models.entities.system_notification_config_entity import (
        SystemNotificationConfigEntity,
    )

    existing = session.execute(select(SystemNotificationConfigEntity)).scalars().all()
    existing_channels = {r.channel for r in existing}
    # 邮件：从 .env 的 SMTP 配置导入
    if "email" not in existing_channels and settings.smtp.host:
        email_cfg = {
            "host": settings.smtp.host,
            "port": settings.smtp.port,
            "username": settings.smtp.username,
            "password": settings.smtp.password,
            "use_tls": settings.smtp.use_tls,
            "from_name": settings.smtp.from_name,
            "from_address": settings.smtp.from_address,
        }
        session.add(
            SystemNotificationConfigEntity(
                channel="email",
                config=email_cfg,
                enabled=True,
            )
        )
        logger.info("Seed notification config created: channel=email")
    # 钉钉：从 .env 导入（如果有配置）
    if "dingtalk" not in existing_channels:
        n = settings.notification
        if n.dingtalk_webhook or n.dingtalk_app_key:
            dt_cfg = {
                "webhook": n.dingtalk_webhook or "",
                "secret": n.dingtalk_secret or "",
                "app_key": n.dingtalk_app_key or "",
                "app_secret": n.dingtalk_app_secret or "",
                "agent_id": n.dingtalk_agent_id or "",
            }
            session.add(
                SystemNotificationConfigEntity(
                    channel="dingtalk",
                    config=dt_cfg,
                    enabled=True,
                )
            )
            logger.info("Seed notification config created: channel=dingtalk")
    # 飞书：从 .env 导入（如果有配置）
    if "feishu" not in existing_channels:
        n = settings.notification
        if n.feishu_webhook or n.feishu_app_id:
            fs_cfg = {
                "webhook": n.feishu_webhook or "",
                "secret": n.feishu_secret or "",
                "app_id": n.feishu_app_id or "",
                "app_secret": n.feishu_app_secret or "",
            }
            session.add(
                SystemNotificationConfigEntity(
                    channel="feishu",
                    config=fs_cfg,
                    enabled=True,
                )
            )
            logger.info("Seed notification config created: channel=feishu")
