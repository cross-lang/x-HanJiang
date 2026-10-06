"""系统运行监控 API（管理员）。

提供 CPU / 内存 / 磁盘 / 网络 / 运行时长等系统资源指标查询，
供仪表盘监控卡片展示。与通知渠道配置、通知发送链路无业务关联。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.api.admin.dependencies import (
    get_system_monitor_service,
    require_user_permission,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.permissions import PermissionCode
from src.services.admin.system_monitor_service import SystemMonitorService

router = APIRouter(prefix="/system-monitor", tags=["管理系统：系统监控"])


@router.get(
    "/system",
    summary="系统监控状态",
    dependencies=[Depends(require_user_permission(PermissionCode.DASHBOARD_VIEW.mark))],
)
@permission(PermissionCode.DASHBOARD_VIEW)
def system_monitor(
    request: Request,
    service: SystemMonitorService = Depends(get_system_monitor_service),
) -> JSONResponse:
    """采集系统运行监控数据（CPU / 内存 / 磁盘 / 网络 / 运行时长）。

    Args:
        request: FastAPI 请求对象。
        service: 系统监控服务实例。

    Returns:
        统一响应，包含 CPU / 内存 / 磁盘 / 网络 / 运行时长指标。
    """
    return success_response(service.get_system_monitor(), request)
