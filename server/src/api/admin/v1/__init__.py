"""API v1 路由包。
在此聚合所有 v1 版本下的业务子路由，统一挂载 /v1 前缀。
未来出 v2 时新建 v2/ 目录，照搬此文件结构即可，router.py 不用动。
"""

from fastapi import APIRouter

from src.api.admin.v1 import (
    alert,
    announcement,
    assistant,
    auth,
    dashboard,
    developer,
    file,
    health,
    log,
    notification,
    notification_config,
    openapi_app,
    openapi_app_registration,
    permission,
    profile,
    role,
    search,
    station,
    system_monitor,
    user,
)
from src.constants import API_VERSION_V1_PREFIX

# v1 聚合路由
v1_router = APIRouter(prefix=API_VERSION_V1_PREFIX)

# 注册健康管理路由
v1_router.include_router(health.router)

# 注册用户管理路由
v1_router.include_router(user.router)

# 注册认证管理路由
v1_router.include_router(auth.router)

# 注册个人中心路由
v1_router.include_router(profile.router)

# 注册角色管理路由
v1_router.include_router(role.router)

# 注册权限管理路由
v1_router.include_router(permission.router)

# 注册审计日志路由（业务审计 + 登录日志）
v1_router.include_router(log.router)

# 注册文件管理路由
v1_router.include_router(file.router)

# 注册公告管理路由
v1_router.include_router(announcement.router)

# 注册通知管理路由（系统通知发布/撤回/列表 + 用户侧通知记录）
v1_router.include_router(notification.router)

# 注册系统通知渠道配置管理路由（渠道配置 / 连通性测试 / 监控状态）
v1_router.include_router(notification_config.router)

# 注册系统监控路由（CPU/内存/磁盘/网络指标，供仪表盘监控卡片）
v1_router.include_router(system_monitor.router)

# 注册告警管理路由
v1_router.include_router(alert.router)

# 注册仪表盘管理路由
v1_router.include_router(dashboard.router)

# 注册站内信管理路由
v1_router.include_router(station.router)

# 注册开放平台管理路由
v1_router.include_router(openapi_app.router)

# 注册开放平台应用审批路由
v1_router.include_router(openapi_app_registration.router)

# 注册开放平台开发者用户管理路由
v1_router.include_router(developer.router)

# 注册搜索路由
v1_router.include_router(search.router)

# 注册 AI 助手路由
v1_router.include_router(assistant.router)

__all__ = ["v1_router"]
