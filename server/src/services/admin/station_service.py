"""站内信服务。
仅调用 StationMessageRepository 存取数据，不直接操作数据库会话。
"""

from datetime import datetime

from src.constants.enums import NotificationEvent, NotificationSource
from src.models.entities.station_message_entity import StationMessageEntity
from src.repositories.station_message_repository import StationMessageRepository

# 来源 → 中文名（与前端站内信页面 SOURCE_LABELS 保持一致）
_SOURCE_LABELS: dict[str, str] = {
    NotificationSource.SYSTEM_NOTICE.value: "系统通知",
    NotificationSource.MANUAL.value: "手动触发",
    NotificationSource.ALERT.value: "系统告警",
    NotificationSource.OPENAPI_APP.value: "开放平台",
}

# 事件类型 → 中文名（与前端站内信页面 EVENT_LABELS 保持一致）
# 覆盖 NotificationEvent 枚举 label（含未入枚举的站内信直发事件，如应用审批）
_EVENT_TYPE_LABELS: dict[str, str] = {
    "system.notice": "系统通知",
    "system.alert": "系统告警",
    "station.message": "站内消息",
    "openapi_app.created": "开放应用创建",
    "openapi_app.updated": "开放应用更新",
    "openapi_app.deleted": "开放应用删除",
    "openapi_app.key_reset": "开放应用密钥重置",
    "openapi_app_registration": "开放应用审批",
    "user.created": "新用户创建",
    "user.deleted": "用户已删除",
    "user.password_changed": "密码修改",
    "user.profile_updated": "资料变更",
    "user.status_changed": "账号状态变更",
    "role.assigned": "角色变更",
    "role.deleted": "角色已删除",
    "permission.granted": "权限授予",
    "permission.revoked": "权限回收",
    "file.uploaded": "文件上传",
    "file.deleted": "文件删除",
    "file.downloaded": "文件下载",
    "login.new_device": "新设备登录",
}


class StationMessageService:
    """站内信服务。

    负责用户站内信收件箱的读（未读数/列表）、写（单发/广播）、
    已读状态维护。站内信本体独立存放于 station_messages 表，
    与系统通知投递明细（notifications_delivery）解耦。
    """

    def __init__(self, repository: StationMessageRepository) -> None:
        """初始化站内信服务。

        Args:
            repository: 站内信数据访问对象
        """
        self._repository = repository

    def unread_count(self, user_id: int) -> int:
        """统计用户未读站内信数量。

        Args:
            user_id: 接收用户 ID

        Returns:
            int: 未读数
        """
        return self._repository.unread_count(user_id)

    def list_messages(
        self,
        user_id: int,
        page: int,
        page_size: int,
        *,
        source: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        keyword: str | None = None,
    ) -> dict:
        """分页查询用户站内信（按时间倒序），支持来源/日期区间/关键词过滤。

        Args:
            user_id: 接收用户 ID
            page: 页码（从 1 开始）
            page_size: 每页数量
            source: 来源过滤
            start_date: 接收起始时间（含）
            end_date: 接收截止时间（含）
            keyword: 关键词（模糊匹配标题/正文）

        Returns:
            dict: 含 total 与 items 的站内信列表结构
        """
        skip = (page - 1) * page_size
        rows, total = self._repository.list_messages(
            user_id=user_id,
            skip=skip,
            limit=page_size,
            source=source,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
        )
        items = [
            {
                "id": r.id,
                "title": r.subject,
                "content": r.content,
                "event_type": r.event_type,
                "source": r.source,
                "is_read": r.is_read,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]
        return {"total": total, "items": items}

    def list_recent(self, user_id: int, limit: int = 10) -> dict:
        """查询用户最近站内信（铃铛下拉用，含未读数，一次返回）。

        Args:
            user_id: 接收用户 ID
            limit: 最近条数（默认 10）

        Returns:
            dict: 含 items（最近站内信）与 unread_count（未读数）
        """
        rows, _ = self._repository.list_messages(
            user_id=user_id,
            skip=0,
            limit=limit,
        )
        items = [
            {
                "id": r.id,
                "title": r.subject,
                "content": r.content,
                "event_type": r.event_type,
                "source": r.source,
                "is_read": r.is_read,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]
        return {"items": items, "unread_count": self._repository.unread_count(user_id)}

    def get_message_detail(self, user_id: int, msg_id: int) -> dict | None:
        """查询用户单条站内信详情。

        Args:
            user_id: 接收用户 ID
            msg_id: 站内信 ID

        Returns:
            dict | None: 站内信详情（含已读时间），不存在返回 None
        """
        msg = self._repository.get_message(user_id, msg_id)
        if msg is None:
            return None
        return {
            "id": msg.id,
            "title": msg.subject,
            "content": msg.content,
            "event_type": msg.event_type,
            "source": msg.source,
            "is_read": msg.is_read,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else "",
            "read_at": msg.read_at.strftime("%Y-%m-%d %H:%M:%S") if msg.read_at else "",
        }

    def export_rows(
        self,
        user_id: int,
        *,
        source: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        keyword: str | None = None,
    ) -> list[dict[str, object]]:
        """查询用户全部站内信用于 CSV 导出（最多 10 万条）。

        Args:
            user_id: 接收用户 ID
            source: 来源过滤
            start_date: 接收起始时间（含）
            end_date: 接收截止时间（含）
            keyword: 关键词过滤

        Returns:
            list[dict[str, object]]: 站内信数据行列表
        """
        rows, _ = self._repository.list_messages(
            user_id=user_id,
            skip=0,
            limit=100000,
            source=source,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
        )
        return [
            {
                "id": r.id,
                "title": r.subject,
                "content": r.content,
                "event_type": _EVENT_TYPE_LABELS.get(r.event_type, r.event_type),
                "source": _SOURCE_LABELS.get(r.source, r.source),
                "status": "已读" if r.is_read else "未读",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                "read_at": r.read_at.strftime("%Y-%m-%d %H:%M:%S") if r.read_at else "",
            }
            for r in rows
        ]

    def mark_read(self, user_id: int, msg_id: int) -> None:
        """标记单条站内信已读。

        Args:
            user_id: 接收用户 ID
            msg_id: 站内信 ID
        """
        msg = self._repository.get_message(user_id, msg_id)
        if msg:
            self._repository.mark_read(msg)
            self._repository.commit()

    def mark_all_read(self, user_id: int) -> None:
        """将用户全部未读站内信标记为已读。

        Args:
            user_id: 接收用户 ID
        """
        self._repository.mark_all_read(user_id)
        self._repository.commit()

    def send_station(
        self,
        user_id: int,
        title: str,
        content: str,
        *,
        source: str = NotificationSource.STATION.value,
        event_type: str | None = None,
        operator_id: int | None = None,
    ) -> None:
        """发送站内信给指定用户（经仓库）。

        Args:
            user_id: 目标用户 ID
            title: 站内信标题
            content: 站内信正文
            source: 消息来源（默认站内信直发）
            event_type: 事件类型（用于前端跳转）
            operator_id: 发送人用户 ID（系统自动为空）
        """
        self._repository.create(
            StationMessageEntity(
                user_id=user_id,
                operator_id=operator_id,
                subject=title,
                content=content,
                source=source,
                event_type=event_type or NotificationEvent.STATION_MESSAGE.mark,
                is_read=False,
            )
        )
        self._repository.commit()

    def send_station_batch(
        self,
        user_ids: list[int],
        title: str,
        content: str,
        *,
        source: str = NotificationSource.SYSTEM_NOTICE.value,
        event_type: str | None = None,
        operator_id: int | None = None,
    ) -> None:
        """批量发送站内信给多个用户（单事务一次提交，供系统通知广播使用）。

        Args:
            user_ids: 目标用户 ID 列表
            title: 站内信标题
            content: 站内信正文
            source: 消息来源（默认系统通知）
            event_type: 站内信事件类型（如 system.notice）
            operator_id: 发送人用户 ID（系统自动为空）
        """
        messages = [
            StationMessageEntity(
                user_id=user_id,
                operator_id=operator_id,
                subject=title,
                content=content,
                source=source,
                event_type=event_type or NotificationEvent.SYSTEM_NOTICE.mark,
                is_read=False,
            )
            for user_id in user_ids
        ]
        self._repository.create_messages(messages)
        self._repository.commit()
