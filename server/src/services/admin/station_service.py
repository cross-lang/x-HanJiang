"""站内信服务。
"""

from datetime import datetime
from typing import Any

from src.constants.enums import NotificationEvent, NotificationSource
from src.models.entities.station_message_entity import StationMessageEntity
from src.repositories.station_message_repository import StationMessageRepository


def _source_label(source: str) -> str:
    """返回来源中文名。

    单一事实源为 NotificationSource 枚举（get_desc_by_mark 反查，未命中回退原始值）；
    station 站内信直发不入该枚举（见枚举 docstring），单独特判映射。

    Args:
        source: 来源标识（system_notice/station/alert/openapi_app）

    Returns:
        str: 来源中文名
    """
    if source == "station":
        return "站内信"
    return NotificationSource.get_desc_by_mark(source)


def _build_event_type_labels() -> dict[str, str]:
    """构建事件类型标识 → 中文名查表（供批量导出等热点场景使用）。

    事件中文名单一事实源为 NotificationEvent 枚举；导出最多 10 万行，
    逐行 get_desc_by_mark 线性反查开销可观，故在批量场景预构建一次 O(1) 查表。

    Returns:
        dict[str, str]: 事件标识 → 中文名映射
    """
    return {event.mark: event.desc for event in NotificationEvent}


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
    ) -> dict[str, Any]:
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
                "event_type_label": NotificationEvent.get_desc_by_mark(r.event_type or ""),
                "source": r.source,
                "source_label": _source_label(r.source),
                "is_read": r.is_read,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]
        return {"total": total, "items": items}

    def list_recent(self, user_id: int, limit: int = 10) -> dict[str, Any]:
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
                "event_type_label": NotificationEvent.get_desc_by_mark(r.event_type or ""),
                "source": r.source,
                "source_label": _source_label(r.source),
                "is_read": r.is_read,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]
        return {"items": items, "unread_count": self._repository.unread_count(user_id)}

    def get_message_detail(self, user_id: int, msg_id: int) -> dict[str, Any] | None:
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
            "event_type_label": NotificationEvent.get_desc_by_mark(msg.event_type or ""),
            "source": msg.source,
            "source_label": _source_label(msg.source),
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
        # 批量导出场景：预构建一次事件类型查表，避免逐行线性反查枚举
        event_type_labels: dict[str, str] = _build_event_type_labels()
        return [
            {
                "id": r.id,
                "title": r.subject,
                "content": r.content,
                "event_type": event_type_labels.get(r.event_type or "", r.event_type or ""),
                "source": _source_label(r.source),
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
        source: str = "station",
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
