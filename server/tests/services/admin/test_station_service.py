#!/usr/bin/env python3
"""站内信服务单元测试。

覆盖 src/services/admin/station_service.py：
    - 读：未读数 / 分页列表 / 最近消息 / 单条详情 / 批量导出（事件标签预查表）
    - 写：标记已读 / 全部已读 / 单发 / 批量发
    - 来源标签：station 直发与枚举反查两种分支

数据访问层用内存 FakeStationMessageRepository 替身，不连真实 DB。
"""

from datetime import UTC, datetime

from src.constants.notification import NotificationEvent, NotificationSource
from src.models.entities.station_message_entity import StationMessageEntity
from src.services.admin.station_service import StationMessageService, _source_label


def _make_row(
    msg_id: int,
    user_id: int = 10,
    subject: str = "标题",
    content: str = "正文",
    source: str = "system_notice",
    event_type: str | None = None,
    is_read: bool = False,
    created_at: datetime | None = None,
    read_at: datetime | None = None,
) -> StationMessageEntity:
    """构造一条站内信实体（created_at 默认固定时间便于断言格式化）。"""
    return StationMessageEntity(
        id=msg_id,
        user_id=user_id,
        subject=subject,
        content=content,
        source=source,
        event_type=event_type or NotificationEvent.SYSTEM_NOTICE.mark,
        is_read=is_read,
        created_at=created_at or datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        read_at=read_at,
    )


class FakeStationMessageRepository:
    """内存版站内信仓库替身，记录写操作。"""

    def __init__(self, rows: list[StationMessageEntity] | None = None) -> None:
        self._rows: dict[int, StationMessageEntity] = {r.id: r for r in (rows or [])}
        self.commits = 0
        self.created: list[StationMessageEntity] = []
        self.batch_created: list[StationMessageEntity] = []
        self.marked_all_read: list[int] = []

    def unread_count(self, user_id: int) -> int:
        return sum(1 for r in self._rows.values() if r.user_id == user_id and not r.is_read)

    def list_messages(self, user_id, skip=0, limit=20, *, source=None, start_date=None, end_date=None, keyword=None):
        rows = [r for r in self._rows.values() if r.user_id == user_id]
        total = len(rows)
        return rows[skip : skip + limit], total

    def get_message(self, user_id: int, msg_id: int) -> StationMessageEntity | None:
        row = self._rows.get(msg_id)
        return row if row and row.user_id == user_id else None

    def mark_read(self, msg: StationMessageEntity) -> None:
        msg.is_read = True

    def mark_all_read(self, user_id: int) -> None:
        self.marked_all_read.append(user_id)
        for r in self._rows.values():
            if r.user_id == user_id and not r.is_read:
                r.is_read = True

    def create(self, message: StationMessageEntity) -> None:
        self.created.append(message)

    def create_messages(self, messages: list[StationMessageEntity]) -> None:
        self.batch_created.extend(messages)

    def commit(self) -> None:
        self.commits += 1


class TestStationRead:
    """站内信读路径。"""

    def setup_method(self) -> None:
        rows = [
            _make_row(1, subject="未读一", is_read=False),
            _make_row(2, subject="已读二", is_read=True),
            _make_row(3, subject="另一个用户的", user_id=99, is_read=False),
        ]
        self.repo = FakeStationMessageRepository(rows)
        self.service = StationMessageService(repository=self.repo)

    def test_unread_count_only_counts_target_user(self) -> None:
        """未读数只统计目标用户的未读消息。"""
        assert self.service.unread_count(10) == 1

    def test_list_messages_formats_labels(self) -> None:
        """列表返回事件/来源中文名与格式化时间。"""
        result = self.service.list_messages(user_id=10, page=1, page_size=10)
        assert result["total"] == 2
        first = result["items"][0]
        assert first["source_label"] == "系统通知"
        assert first["event_type_label"] == "系统通知（发布/维护广播站内信）"
        assert first["created_at"] == "2026-01-02 03:04"

    def test_list_recent_includes_unread_count(self) -> None:
        """最近消息下拉一次返回列表与未读数。"""
        result = self.service.list_recent(user_id=10, limit=5)
        assert result["unread_count"] == 1
        assert len(result["items"]) == 2

    def test_get_message_detail_found(self) -> None:
        """存在的消息详情含已读时间。"""
        result = self.service.get_message_detail(user_id=10, msg_id=2)
        assert result is not None
        assert result["title"] == "已读二"
        assert result["is_read"] is True

    def test_get_message_detail_not_found(self) -> None:
        """不存在或不属于该用户 → 返回 None。"""
        assert self.service.get_message_detail(user_id=10, msg_id=404) is None
        assert self.service.get_message_detail(user_id=10, msg_id=3) is None  # 属于其他用户

    def test_export_rows_uses_prebuilt_labels(self) -> None:
        """批量导出走预查表，状态映射已读/未读。"""
        rows = self.service.export_rows(user_id=10)
        assert len(rows) == 2
        status_map = {r["title"]: r["status"] for r in rows}
        assert status_map["未读一"] == "未读"
        assert status_map["已读二"] == "已读"
        # 事件列输出中文名而非原始 mark
        assert rows[0]["event_type"] == "系统通知（发布/维护广播站内信）"


class TestStationWrite:
    """站内信写路径。"""

    def setup_method(self) -> None:
        self.repo = FakeStationMessageRepository([_make_row(1, is_read=False)])
        self.service = StationMessageService(repository=self.repo)

    def test_mark_read_found(self) -> None:
        """标记已读命中 → 置位并提交。"""
        self.service.mark_read(user_id=10, msg_id=1)
        assert self.repo._rows[1].is_read is True
        assert self.repo.commits == 1

    def test_mark_read_missing_no_op(self) -> None:
        """标记不存在的消息 → 无副作用不提交。"""
        self.service.mark_read(user_id=10, msg_id=999)
        assert self.repo.commits == 0

    def test_mark_all_read(self) -> None:
        """全部已读 → 仓库批量方法被调用并提交。"""
        self.service.mark_all_read(user_id=10)
        assert self.repo.marked_all_read == [10]
        assert self.repo.commits == 1

    def test_send_station_defaults_event(self) -> None:
        """单发：未指定事件类型时回退为站内消息事件。"""
        self.service.send_station(user_id=5, title="hi", content="c", source="station")
        assert len(self.repo.created) == 1
        msg = self.repo.created[0]
        assert msg.event_type == NotificationEvent.STATION_MESSAGE.mark
        assert msg.source == "station"
        assert self.repo.commits == 1

    def test_send_station_batch(self) -> None:
        """批量发：一次构造多条并单事务提交。"""
        self.service.send_station_batch(
            user_ids=[1, 2, 3],
            title="广播",
            content="内容",
            source=NotificationSource.SYSTEM_NOTICE.value,
        )
        assert len(self.repo.batch_created) == 3
        assert {m.user_id for m in self.repo.batch_created} == {1, 2, 3}
        assert self.repo.commits == 1


class TestSourceLabel:
    """来源标签映射分支。"""

    def test_station_source_label(self) -> None:
        """station 直发来源特判为'站内信'。"""
        assert _source_label("station") == "站内信"
        assert _source_label("alert") == "系统告警"
