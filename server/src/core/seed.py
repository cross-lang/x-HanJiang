#!/usr/bin/env python3
"""
种子数据管理模块

应用启动时检测并自动创建系统内置种子数据：
    1. 超级管理员角色（roles 表，role_type=system，role_code=super_admin）
    2. 超级管理员用户（users 表，username=superadmin，绑定上述角色）
    3. 内置权限（permissions 表）
    4. 角色权限关联（role_permissions 表，将全部权限绑定到超级管理员角色）

若数据已存在则跳过，保证幂等。

Functions:
    init_seed_data: 初始化种子数据（幂等）
"""

from sqlalchemy import select

from src.constants.enums import SystemRoleCode
from src.core.logger import logger
from src.utils.security import hash_password
from src.infras.database import get_cached_database_provider
from src.infras.database import MySqlProvider
from src.models.entities.menu_entity import MenuEntity
from src.models.entities.user_entity import (
    PermissionEntity,
    RoleEntity,
    RolePermissionEntity,
    UserEntity,
)

# ── 超级管理员 ──────────────────────────────────────────────
_SEED_ROLE_CODE = SystemRoleCode.SUPER_ADMIN.mark
_SEED_ROLE_NAME = "超级管理员"

# ── 管理员 ──────────────────────────────────────────────────
_SEED_ADMIN_ROLE_CODE = SystemRoleCode.ADMIN.mark
_SEED_ADMIN_ROLE_NAME = "管理员"

# ── 普通用户 ────────────────────────────────────────────────
_SEED_USER_ROLE_CODE = "user"
_SEED_USER_ROLE_NAME = "普通用户"
_SEED_ADMIN_USERNAME = "superadmin"
_SEED_ADMIN_PASSWORD = "admin@123456"
_SEED_ADMIN_EMAIL = "superadmin@system.local"

# ── 内置权限定义 ──────────────────────────────────────────────
# (perm_code, perm_name, module, operation, description, sort_order)
_SEED_PERMISSIONS: list[tuple[str, str, str, str, str, int]] = [
    ("user:view", "查看用户", "user", "view", "查看用户列表与详情", 1),
    ("user:create", "创建用户", "user", "create", "创建新用户", 2),
    ("user:edit", "编辑用户", "user", "edit", "编辑用户信息", 3),
    ("user:delete", "删除用户", "user", "delete", "删除用户", 4),
    ("user:export", "导出用户", "user", "export", "导出用户列表", 5),
    ("user:import", "导入用户", "user", "import", "导入用户列表", 6),
    ("role:view", "查看角色", "role", "view", "查看角色列表与详情", 10),
    ("role:create", "创建角色", "role", "create", "创建新角色", 11),
    ("role:edit", "编辑角色", "role", "edit", "编辑角色信息", 12),
    ("role:delete", "删除角色", "role", "delete", "删除角色", 13),
    ("file:view", "查看文件", "file", "view", "查看文件列表与详情", 20),
    ("file:create", "上传文件", "file", "create", "上传文件", 21),
    ("file:delete", "删除文件", "file", "delete", "删除文件", 22),
    ("audit_log:view", "查看审计日志", "audit_log", "view", "查看业务审计日志", 30),
    ("audit_log:export", "导出审计日志", "audit_log", "export", "导出审计日志CSV", 31),
    ("login_log:view", "查看登录日志", "login_log", "view", "查看登录日志", 35),
    ("login_log:export", "导出登录日志", "login_log", "export", "导出登录日志CSV", 36),
    ("notification:view", "查看通知", "notification", "view", "查看通知记录", 40),
    ("notification:create", "创建通知", "notification", "create", "手动发送通知", 41),
    ("alert:broadcast", "广播告警", "alert", "broadcast", "向全体用户广播告警", 50),
    ("maintenance:notify", "发送维护通知", "maintenance", "notify", "向全体用户发送维护通知", 51),
    ("openapi_app:view", "查看开放平台应用", "openapi_app", "view", "查看开放平台应用列表", 60),
    ("openapi_app:create", "创建开放平台应用", "openapi_app", "create", "创建开放平台应用", 61),
    ("openapi_app:edit", "编辑开放平台应用", "openapi_app", "edit", "编辑开放平台应用", 62),
    ("openapi_app:delete", "删除开放平台应用", "openapi_app", "delete", "删除开放平台应用", 63),
    ("dashboard:view", "查看仪表盘", "dashboard", "view", "获取仪表盘关键指标", 70),
    ("swagger:view", "查看Swagger文档", "swagger", "view", "查看API Swagger文档", 80),
]

# ── 内置菜单定义 ──────────────────────────────────────────────
# (parent_title 或 0, title, path, icon, perm_code, sort_order, type)
# parent 为 0 表示根菜单
_SEED_MENUS = [
    # 根菜单
    (0, "首页", "/dashboard", "Odometer", None, 1, "menu"),
    (0, "仪表盘", "/panel", "DataAnalysis", "dashboard:view", 2, "menu"),
    (0, "系统管理", "/system", "Setting", None, 3, "directory"),
    # 系统管理子菜单
    ("系统管理", "用户管理", "/users", "User", "user:view", 1, "menu"),
    ("系统管理", "角色管理", "/roles", "UserFilled", "role:view", 2, "menu"),
    ("系统管理", "权限管理", "/permissions", "Lock", "role:view", 3, "menu"),
    ("系统管理", "审计日志", "/audit", "Document", "audit_log:view", 4, "menu"),
    ("系统管理", "登录日志", "/audit/login", "User", "login_log:view", 5, "menu"),
    ("系统管理", "文件管理", "/files", "Folder", "file:view", 6, "menu"),
    # 接口管理
    (0, "接口管理", "/apis", "Link", None, 4, "directory"),
    ("接口管理", "Swagger文档", "/apis/swagger", "Document", "swagger:view", 1, "menu"),
    # 开放平台
    (0, "开放平台", "/open", "Connection", None, 5, "directory"),
    ("开放平台", "应用管理", "/apps", "Grid", "openapi_app:view", 1, "menu"),
    ("开放平台", "权限管理", "/app-scopes", "Lock", "openapi_app:view", 2, "menu"),
]



def init_seed_data() -> None:
    """初始化系统种子数据（幂等，可重复调用）。"""
    session = get_cached_database_provider().get_session_factory()()
    try:
        # 1. 权限
        perm_map: dict[str, PermissionEntity] = {}
        for code, name, module, op, desc, sort in _SEED_PERMISSIONS:
            perm = session.execute(
                select(PermissionEntity).where(PermissionEntity.perm_code == code)
            ).scalars().first()
            if perm is None:
                perm = PermissionEntity(
                    perm_code=code,
                    perm_name=name,
                    module=module,
                    operation=op,
                    description=desc,
                    sort_order=sort,
                )
                session.add(perm)
                session.flush()
                logger.info(f"Seed permission created: perm_code={code}")
            perm_map[code] = perm

        # 2. 超级管理员角色
        role = session.execute(
            select(RoleEntity).where(RoleEntity.role_code == _SEED_ROLE_CODE)
        ).scalars().first()
        if role is None:
            role = RoleEntity(
                role_name=_SEED_ROLE_NAME,
                role_code=_SEED_ROLE_CODE,
                description="系统内置超级管理员角色，拥有全部权限",
                role_type="system",
                status="enabled",
            )
            session.add(role)
            session.flush()
            logger.info(f"Seed role created: role_code={_SEED_ROLE_CODE}")

        # 3. 超级管理员角色 → 绑定全部权限
        for perm in perm_map.values():
            _ensure_role_permission(session, role.id, perm.id)

        # 3.5 管理员角色（除不能管理超级管理员外，其余权限相同）
        admin_role = session.execute(
            select(RoleEntity).where(RoleEntity.role_code == _SEED_ADMIN_ROLE_CODE)
        ).scalars().first()
        if admin_role is None:
            admin_role = RoleEntity(
                role_name=_SEED_ADMIN_ROLE_NAME,
                role_code=_SEED_ADMIN_ROLE_CODE,
                description="系统内置管理员角色，拥有除超级管理员管理外的全部权限",
                role_type="system",
                status="enabled",
            )
            session.add(admin_role)
            session.flush()
            logger.info(f"Seed role created: role_code={_SEED_ADMIN_ROLE_CODE}")

        # 管理员角色 → 绑定全部权限（幂等，无论角色是否新建都执行）
        for perm in perm_map.values():
            _ensure_role_permission(session, admin_role.id, perm.id)

        # 3.6 普通用户角色（只能查看首页，无额外权限）
        user_role = session.execute(
            select(RoleEntity).where(RoleEntity.role_code == _SEED_USER_ROLE_CODE)
        ).scalars().first()
        if user_role is None:
            user_role = RoleEntity(
                role_name=_SEED_USER_ROLE_NAME,
                role_code=_SEED_USER_ROLE_CODE,
                description="系统内置普通用户角色，仅可查看首页",
                role_type="system",
                status="enabled",
            )
            session.add(user_role)
            session.flush()
            logger.info(f"Seed role created: role_code={_SEED_USER_ROLE_CODE}")

        # 4. 超级管理员用户
        admin = session.execute(
            select(UserEntity).where(UserEntity.username == _SEED_ADMIN_USERNAME)
        ).scalars().first()
        if admin is None:
            admin = UserEntity(
                username=_SEED_ADMIN_USERNAME,
                email=_SEED_ADMIN_EMAIL,
                password_hash=hash_password(_SEED_ADMIN_PASSWORD),
                phone=None,
                avatar_url=None,
                role_id=role.id,
                status="active",
            )
            session.add(admin)
            session.flush()
            # 绑定超级管理员角色
            session.add(RolePermissionEntity.__class__ if False else __import__('src.models.entities.user_entity', fromlist=['UserRoleEntity']).UserRoleEntity(
                user_id=admin.id, role_id=role.id
            ))
            logger.info(f"Seed admin user created: username={_SEED_ADMIN_USERNAME}")

        # 5. 菜单数据
        _seed_menus(session)

        session.commit()
        logger.info("Seed data initialization completed")
    except Exception as e:  # noqa: BLE001
        session.rollback()
        logger.warning(f"Seed data initialization skipped: {e}")
    finally:
        session.close()


def _ensure_role_permission(session, role_id: int, permission_id: int) -> None:
    """确保角色权限关联存在，不存在则创建。"""
    relation = session.execute(
        select(RolePermissionEntity).where(
            RolePermissionEntity.role_id == role_id,
            RolePermissionEntity.permission_id == permission_id,
        )
    ).scalars().first()
    if relation is None:
        relation = RolePermissionEntity(
            role_id=role_id,
            permission_id=permission_id,
        )
        session.add(relation)
        session.flush()

def _seed_menus(session) -> None:
    """初始化菜单数据（幂等）。"""
    # 先查已有菜单，按 title 建索引
    existing = session.execute(select(MenuEntity)).scalars().all()
    title_map = {m.title: m for m in existing}

    parent_map: dict[str, MenuEntity] = {}
    for item in existing:
        parent_map[item.title] = item

    for parent_title, title, path, icon, perm_code, sort_order, mtype in _SEED_MENUS:
        if title in title_map:
            continue
        parent_id = 0
        if parent_title != 0:
            parent = parent_map.get(parent_title)
            if parent:
                parent_id = parent.id
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
        logger.info(f"Seed menu created: title={title}")
