"""通知子系统。
集中管理通知调度、模板渲染、投递明细与失败重试。
供 services/ 层调用，不直接暴露给 API 层。
"""

from src.notification.dispatcher import NotificationDispatcher
from src.notification.template import reload_templates, render_template

__all__ = [
    "NotificationDispatcher",
    "render_template",
    "reload_templates",
]
