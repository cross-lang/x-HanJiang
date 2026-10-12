#!/usr/bin/env python3
"""AI 助手数据访问层（assistant_repository）单元测试。

采用「真实 Repository + 脚本化 FakeSession」手法：仓储对象照常实例化（显式注入
session），但 session 用 MagicMock 替身，只断言仓储发起的调用与分支行为：
    - 实体存在 / 不存在两类分支（软删除、置顶、摘要、标题更新）
    - 消息追加、消息列表正序反转、计数、窗口外最旧消息、批量删除空列表短路
    - 反馈追加、用户档案 upsert（新建走 insert / 已有走覆盖）

不连真实 MySQL，不触网。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.repositories.assistant_repository import (
    AssistantConversationRepository,
    AssistantFeedbackRepository,
    AssistantMessageRepository,
    AssistantUserProfileRepository,
)


def _session_first(value: object | None) -> MagicMock:
    """构造 session 替身：execute().scalars().first() 返回脚本值。"""
    session = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = value
    return session


def _session_all(values: list) -> MagicMock:
    """构造 session 替身：execute().scalars().all() 返回脚本列表。"""
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = list(values)
    return session


# ============================================================
# AssistantConversationRepository
# ============================================================


class TestConversationRepository:
    """会话仓储分支测试。"""

    def test_get_by_id_returns_scalar(self):
        """按 ID 查询直接透传 session 首行结果。"""
        entity = SimpleNamespace(id=1)
        repo = AssistantConversationRepository(session=_session_first(entity))
        assert repo.get_by_id(1) is entity

    def test_list_by_user_returns_rows(self):
        """按用户列表透传 session 行集。"""
        rows = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        repo = AssistantConversationRepository(session=_session_all(rows))
        assert repo.list_by_user(user_id=7, limit=10) == rows

    def test_soft_delete_missing_entity_noop(self):
        """软删除不存在的会话：直接返回，不 flush。"""
        session = _session_first(None)
        repo = AssistantConversationRepository(session=session)
        repo.soft_delete(conversation_id=404)
        session.flush.assert_not_called()

    def test_soft_delete_marks_deleted_at(self):
        """软删除存在的会话：写入 deleted_at 并 flush。"""
        entity = SimpleNamespace(id=5, deleted_at=None)
        session = _session_first(entity)
        repo = AssistantConversationRepository(session=session)
        repo.soft_delete(conversation_id=5)
        assert entity.deleted_at is not None
        session.flush.assert_called_once()

    def test_update_pinned_branches(self):
        """置顶更新：实体缺失静默返回；存在则改写标志并 flush。"""
        missing = AssistantConversationRepository(session=_session_first(None))
        missing.update_pinned(1, True)  # 不抛异常即可
        missing.session.flush.assert_not_called()

        entity = SimpleNamespace(id=6, is_pinned=False)
        session = _session_first(entity)
        repo = AssistantConversationRepository(session=session)
        repo.update_pinned(6, True)
        assert entity.is_pinned is True
        session.flush.assert_called_once()

    def test_update_summary_branches(self):
        """摘要更新：缺失静默返回；存在则改写 summary 并 flush。"""
        entity = SimpleNamespace(id=7, summary=None)
        session = _session_first(entity)
        repo = AssistantConversationRepository(session=session)
        repo.update_summary(7, "新摘要")
        assert entity.summary == "新摘要"
        session.flush.assert_called_once()

    def test_update_title_branches(self):
        """标题更新：缺失静默返回；存在则改写 title 并 flush。"""
        missing = AssistantConversationRepository(session=_session_first(None))
        missing.update_title(1, "任意标题")  # 不抛异常
        entity = SimpleNamespace(id=8, title=None)
        session = _session_first(entity)
        repo = AssistantConversationRepository(session=session)
        repo.update_title(8, "用户咨询公告")
        assert entity.title == "用户咨询公告"
        session.flush.assert_called_once()


# ============================================================
# AssistantMessageRepository
# ============================================================


class TestMessageRepository:
    """消息仓储测试。"""

    def test_add_message_creates_entity(self):
        """追加消息：构造实体并经 session.add 落库、flush。"""
        session = MagicMock()
        repo = AssistantMessageRepository(session=session)
        entity = repo.add_message(conversation_id=3, role="user", content="你好")
        assert entity.conversation_id == 3
        assert entity.role == "user"
        assert entity.content == "你好"
        session.add.assert_called_once_with(entity)
        session.flush.assert_called_once()

    def test_list_by_conversation_reversed_to_chronological(self):
        """列表查询把「新→旧」行集反转为「旧→新」正序。"""
        newest = SimpleNamespace(id=20)
        oldest = SimpleNamespace(id=1)
        repo = AssistantMessageRepository(session=_session_all([newest, oldest]))
        rows = repo.list_by_conversation(conversation_id=3)
        assert rows == [oldest, newest]

    def test_count_by_conversation(self):
        """计数透传 session 标量；NULL 结果兜底为 0。"""
        session = MagicMock()
        session.execute.return_value.scalar.return_value = 9
        repo = AssistantMessageRepository(session=session)
        assert repo.count_by_conversation(3) == 9

        session2 = MagicMock()
        session2.execute.return_value.scalar.return_value = None
        repo2 = AssistantMessageRepository(session=session2)
        assert repo2.count_by_conversation(3) == 0

    def test_list_oldest_outside_window(self):
        """窗口外最旧消息透传行集。"""
        rows = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        repo = AssistantMessageRepository(session=_session_all(rows))
        assert repo.list_oldest_outside_window(conversation_id=3, keep_count=10, limit=4) == rows

    def test_delete_by_ids_empty_short_circuits(self):
        """空主键列表短路：不发起任何 SQL。"""
        session = MagicMock()
        repo = AssistantMessageRepository(session=session)
        repo.delete_by_ids([])
        session.execute.assert_not_called()
        session.flush.assert_not_called()

    def test_delete_by_ids_executes_and_flushes(self):
        """非空主键列表：执行删除并 flush。"""
        session = MagicMock()
        repo = AssistantMessageRepository(session=session)
        repo.delete_by_ids([1, 2, 3])
        session.execute.assert_called_once()
        session.flush.assert_called_once()


# ============================================================
# AssistantFeedbackRepository
# ============================================================


class TestFeedbackRepository:
    """反馈仓储测试。"""

    def test_add_feedback_persists_entity(self):
        """写入一条反馈：实体字段齐全并落库。"""
        session = MagicMock()
        repo = AssistantFeedbackRepository(session=session)
        entity = repo.add_feedback(
            conversation_id=3,
            message_id=100,
            user_id=7,
            positive=False,
            comment="答非所问",
        )
        assert entity.conversation_id == 3
        assert entity.message_id == 100
        assert entity.positive is False
        assert entity.comment == "答非所问"
        session.add.assert_called_once_with(entity)
        session.flush.assert_called_once()


# ============================================================
# AssistantUserProfileRepository
# ============================================================


class TestUserProfileRepository:
    """用户档案仓储（upsert 新建/覆盖双分支）测试。"""

    def test_get_by_user_returns_row(self):
        """按用户透传首行结果（无记录为 None）。"""
        repo = AssistantUserProfileRepository(session=_session_first(None))
        assert repo.get_by_user(7) is None

    def test_upsert_new_user_inserts(self):
        """无档案记录：新建实体，版本号在传入基础上 +1。"""
        session = MagicMock()
        session.execute.return_value.scalars.return_value.first.return_value = None
        repo = AssistantUserProfileRepository(session=session)
        repo.upsert(user_id=7, profile="- 管理员", version=0)
        session.add.assert_called_once()
        added = session.add.call_args.args[0]
        assert added.user_id == 7
        assert added.profile == "- 管理员"
        assert added.version == 1  # 0 + 1
        session.flush.assert_called_once()

    def test_upsert_existing_user_overwrites(self):
        """已有档案：覆盖文本并递增版本，不新增实体。"""
        existing = SimpleNamespace(id=1, user_id=7, profile="旧档案", version=3)
        session = MagicMock()
        session.execute.return_value.scalars.return_value.first.return_value = existing
        repo = AssistantUserProfileRepository(session=session)
        repo.upsert(user_id=7, profile="新档案", version=3)
        assert existing.profile == "新档案"
        assert existing.version == 4  # 3 + 1
        session.add.assert_not_called()
        session.flush.assert_called_once()
