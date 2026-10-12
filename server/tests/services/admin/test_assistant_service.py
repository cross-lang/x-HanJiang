#!/usr/bin/env python3
"""AI 助手编排服务（AssistantService）单元测试。

测试 src/services/admin/assistant_service.py：
    - 会话管理：创建 / 列表 / 消息查询 / 置顶 / 删除（含归属校验 NotFound 分支）
    - 反馈保存（含归属校验）
    - chat_stream：功能开关关闭、正常一轮、会话归属不符、大模型异常兜底
    - 通道保护 _stream_with_protection：超时 / 客户端断连 / 异常兜底
    - 收尾辅助：导航兜底回复 FAQ 命中、会话命名、长期记忆节流、跳转审计

LLM 一律 fake（get_llm_provider 打补丁返回内存替身）；仓储全部内存 fake，
不连真实 MySQL / Redis，不触网。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from src.constants.assistant import (
    ASSISTANT_FALLBACK_MESSAGE,
    AssistantEventType,
)
from src.core.config import settings
from src.core.exceptions import ExternalServiceException, NotFoundException
from src.infras.llm import ContentDelta, LLMChatResult, LLMProvider
from src.models.entities.assistant_entity import (
    AssistantConversationEntity,
    AssistantMessageEntity,
)
from src.schemas.admin.assistant import FeedbackRequest
from src.schemas.admin.auth import CurrentUser
from src.services.admin.assistant_service import AssistantService

# ============================================================
# 测试替身
# ============================================================


class FakeConversationRepo:
    """会话仓储内存替身（dict 存储，记录写操作）。"""

    model_class = AssistantConversationEntity

    def __init__(self) -> None:
        self._items: dict[int, AssistantConversationEntity] = {}
        self._next = 1
        self.commits = 0
        self.pinned_updates: list[tuple[int, bool]] = []
        self.deleted: list[int] = []
        self.title_updates: list[tuple[int, str]] = []

    def create(self, entity: AssistantConversationEntity) -> AssistantConversationEntity:
        entity.id = self._next
        self._next += 1
        self._items[entity.id] = entity
        return entity

    def get_by_id(self, entity_id: int) -> AssistantConversationEntity | None:
        return self._items.get(entity_id)

    def list_by_user(self, user_id: int, limit: int = 20) -> list[AssistantConversationEntity]:
        return [c for c in self._items.values() if c.user_id == user_id][:limit]

    def update_pinned(self, conversation_id: int, pinned: bool) -> None:
        self.pinned_updates.append((conversation_id, pinned))
        self._items[conversation_id].is_pinned = pinned

    def soft_delete(self, conversation_id: int) -> None:
        self.deleted.append(conversation_id)
        self._items.pop(conversation_id, None)

    def update_summary(self, conversation_id: int, summary: str) -> None:
        """滚动摘要端口（本文件用例不直接断言）。"""

    def update_title(self, conversation_id: int, title: str) -> None:
        self.title_updates.append((conversation_id, title))
        self._items[conversation_id].title = title

    def commit(self) -> None:
        self.commits += 1


class FakeMessageRepo:
    """消息仓储内存替身（session 给 MagicMock，供工具注册表装配）。"""

    def __init__(self) -> None:
        self.session = MagicMock()
        self._items: list[AssistantMessageEntity] = []
        self._next = 1
        self.commits = 0

    def add_message(self, conversation_id: int, role: str, content: str) -> AssistantMessageEntity:
        entity = AssistantMessageEntity(id=self._next, conversation_id=conversation_id, role=role, content=content)
        self._next += 1
        self._items.append(entity)
        return entity

    def list_by_conversation(self, conversation_id: int, limit: int = 100):
        return [m for m in self._items if m.conversation_id == conversation_id][-limit:]

    def count_by_conversation(self, conversation_id: int) -> int:
        return sum(1 for m in self._items if m.conversation_id == conversation_id)

    def list_oldest_outside_window(self, conversation_id: int, keep_count: int, limit: int = 10):
        return []

    def delete_by_ids(self, message_ids: list[int]) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1


class FakeFeedbackRepo:
    """反馈仓储内存替身。"""

    def __init__(self) -> None:
        self.added: list[dict] = []
        self.commits = 0

    def add_feedback(self, conversation_id, message_id, user_id, positive, comment):
        self.added.append(
            {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "user_id": user_id,
                "positive": positive,
                "comment": comment,
            }
        )
        return MagicMock()

    def commit(self) -> None:
        self.commits += 1


class FakeLLM(LLMProvider):
    """LLM 替身：chat_stream 产出预置事件；chat 返回固定主题或抛错。"""

    def __init__(
        self,
        stream_events: list | None = None,
        chat_content: str = "会话主题",
        chat_error: Exception | None = None,
    ) -> None:
        self._events = list(stream_events or [])
        self._chat_content = chat_content
        self._chat_error = chat_error
        self.chat_calls = 0

    def chat_stream(self, messages, tools=None, temperature=None, max_tokens=None):
        yield from self._events

    def chat(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMChatResult:
        self.chat_calls += 1
        if self._chat_error is not None:
            raise self._chat_error
        return LLMChatResult(raw_message={}, content=self._chat_content, tool_calls=[])

    def summarize(self, text: str) -> str:
        return "压缩摘要"


def _make_user(permissions: list[str] | None = None) -> CurrentUser:
    return CurrentUser(
        id=7,
        username="tester",
        email="tester@example.com",
        name="测试用户",
        status="enabled",
        permissions=permissions if permissions is not None else ["*"],
    )


def _build_service(llm: FakeLLM | None = None):
    """组装服务与三套内存替身（get_llm_provider 打补丁，不连真实模型）。"""
    conv_repo = FakeConversationRepo()
    msg_repo = FakeMessageRepo()
    fb_repo = FakeFeedbackRepo()
    fake_llm = llm or FakeLLM()
    with patch("src.services.admin.assistant_service.get_llm_provider", return_value=fake_llm):
        service = AssistantService(conv_repo, msg_repo, fb_repo)
    return service, conv_repo, msg_repo, fb_repo, fake_llm


def _new_conversation(conv_repo: FakeConversationRepo, user_id: int = 7) -> AssistantConversationEntity:
    """直接在仓储中造一个会话。"""
    return conv_repo.create(AssistantConversationEntity(user_id=user_id))


# ============================================================
# 会话管理
# ============================================================


class TestConversationManagement:
    """会话 CRUD 与归属校验测试。"""

    def test_create_conversation_persists(self):
        """创建会话：落库并提交。"""
        service, conv_repo, _, _, _ = _build_service()
        entity = service.create_conversation(user_id=7)
        assert entity.id is not None
        assert entity.user_id == 7
        assert conv_repo.commits == 1

    def test_list_conversations_scoped_to_user(self):
        """列表只返回当前用户的会话。"""
        service, conv_repo, _, _, _ = _build_service()
        _new_conversation(conv_repo, 7)
        _new_conversation(conv_repo, 7)
        _new_conversation(conv_repo, 8)
        result = service.list_conversations(user_id=7)
        assert len(result) == 2

    def test_list_messages_not_found(self):
        """消息查询：会话不存在抛 NotFound。"""
        service, _, _, _, _ = _build_service()
        with pytest.raises(NotFoundException):
            service.list_messages(conversation_id=999, user_id=7)

    def test_list_messages_wrong_owner(self):
        """消息查询：会话归属他人抛 NotFound。"""
        service, conv_repo, _, _, _ = _build_service()
        conv = _new_conversation(conv_repo, user_id=8)
        with pytest.raises(NotFoundException):
            service.list_messages(conversation_id=conv.id, user_id=7)

    def test_list_messages_ok(self):
        """消息查询：归属正确时按仓储返回（默认上限常量）。"""
        service, conv_repo, msg_repo, _, _ = _build_service()
        conv = _new_conversation(conv_repo, 7)
        msg_repo.add_message(conv.id, "user", "问题")
        msg_repo.add_message(conv.id, "assistant", "回答")
        result = service.list_messages(conversation_id=conv.id, user_id=7)
        assert len(result) == 2

    def test_update_pinned(self):
        """置顶：不存在抛 NotFound；存在则翻转并提交。"""
        service, conv_repo, _, _, _ = _build_service()
        with pytest.raises(NotFoundException):
            service.update_pinned(user_id=7, conversation_id=999, pinned=True)
        conv = _new_conversation(conv_repo, 7)
        updated = service.update_pinned(user_id=7, conversation_id=conv.id, pinned=True)
        assert updated.is_pinned is True
        assert conv_repo.pinned_updates == [(conv.id, True)]
        assert conv_repo.commits >= 1

    def test_delete_conversation(self):
        """删除：不存在抛 NotFound；存在则软删并提交。"""
        service, conv_repo, _, _, _ = _build_service()
        with pytest.raises(NotFoundException):
            service.delete_conversation(user_id=7, conversation_id=999)
        conv = _new_conversation(conv_repo, 7)
        service.delete_conversation(user_id=7, conversation_id=conv.id)
        assert conv_repo.deleted == [conv.id]
        assert conv_repo.get_by_id(conv.id) is None

    def test_save_feedback(self):
        """反馈：归属不符抛 NotFound；正确则落库提交。"""
        service, conv_repo, _, fb_repo, _ = _build_service()
        conv = _new_conversation(conv_repo, 7)
        with pytest.raises(NotFoundException):
            service.save_feedback(
                user_id=7, feedback=FeedbackRequest(conversation_id=999, message_id=1, positive=True, comment=None)
            )
        service.save_feedback(
            user_id=7,
            feedback=FeedbackRequest(conversation_id=conv.id, message_id=100, positive=False, comment="太长了"),
        )
        assert fb_repo.added == [
            {
                "conversation_id": conv.id,
                "message_id": 100,
                "user_id": 7,
                "positive": False,
                "comment": "太长了",
            }
        ]
        assert fb_repo.commits == 1


# ============================================================
# chat_stream 主入口
# ============================================================


class TestChatStream:
    """对话入口事件流测试。"""

    def test_disabled_returns_error_and_done(self, monkeypatch: pytest.MonkeyPatch):
        """功能开关关闭：直接下发 error + done（message_id 为空）。"""
        monkeypatch.setattr(settings.ai, "enabled", False)
        service, _, msg_repo, _, _ = _build_service()
        events = list(service.chat_stream(_make_user(), None, "你好"))
        assert events[0]["type"] == AssistantEventType.ERROR.mark
        assert events[1]["type"] == AssistantEventType.DONE.mark
        assert events[1]["message_id"] is None
        assert msg_repo.count_by_conversation(0) == 0  # 不落库

    def test_normal_round_emits_events_and_persists(self):
        """正常一轮：thinking → token → done；用户/助手消息落库；会话自动命名。"""
        llm = FakeLLM(stream_events=[ContentDelta(text="你好，有什么可以帮你")])
        service, conv_repo, msg_repo, _, _ = _build_service(llm)
        events = list(service.chat_stream(_make_user(), None, "你好"))
        types = [e["type"] for e in events]
        assert types[0] == AssistantEventType.THINKING.mark
        assert AssistantEventType.TOKEN.mark in types
        assert types[-1] == AssistantEventType.DONE.mark
        # done 携带助手消息 ID
        done = events[-1]
        assert done["message_id"] is not None
        # 用户消息 + 助手回复共两条
        conv_id = done["conversation_id"]
        assert msg_repo.count_by_conversation(conv_id) == 2
        # 未命名会话经 LLM 归纳标题
        assert conv_repo.get_by_id(conv_id).title == "会话主题"

    def test_wrong_owner_conversation_returns_error(self):
        """会话归属他人：error + done，不落库任何消息。"""
        service, conv_repo, msg_repo, _, llm = _build_service()
        conv = _new_conversation(conv_repo, user_id=8)
        events = list(service.chat_stream(_make_user(), conv.id, "你好"))
        assert events[0]["type"] == AssistantEventType.ERROR.mark
        assert events[1]["message_id"] is None
        assert msg_repo.count_by_conversation(conv.id) == 0

    def test_existing_valid_conversation_reused(self):
        """传入归属正确的已有会话：复用该会话，消息落到该会话下。"""
        llm = FakeLLM(stream_events=[ContentDelta(text="继续回答")])
        service, conv_repo, msg_repo, _, _ = _build_service(llm)
        conv = _new_conversation(conv_repo, user_id=7)
        events = list(service.chat_stream(_make_user(), conv.id, "追问"))
        done = events[-1]
        assert done["type"] == AssistantEventType.DONE.mark
        assert done["conversation_id"] == conv.id
        assert msg_repo.count_by_conversation(conv.id) == 2

    def test_external_service_error_saves_fallback(self):
        """大模型服务异常：先落库兜底回复，再 error + done（携带兜底消息 ID）。"""
        llm = FakeLLM()
        service, conv_repo, msg_repo, _, _ = _build_service(llm)
        # 组装上下文阶段抛 ExternalServiceException
        service._memory_facade.build_context = MagicMock(side_effect=ExternalServiceException(message="模型服务异常"))
        events = list(service.chat_stream(_make_user(), None, "你好"))
        types = [e["type"] for e in events]
        assert types == [AssistantEventType.ERROR.mark, AssistantEventType.DONE.mark]
        done = events[-1]
        assert done["message_id"] is not None  # 兜底回复已落库
        # 用户消息与兜底回复均已落库（done 事件回传的 conversation_id 为入参 None，
        # 故直接在消息仓储中核对内容）
        contents = [m.content for m in msg_repo._items]
        assert "你好" in contents
        assert ASSISTANT_FALLBACK_MESSAGE in contents
        assert llm.chat_calls == 0  # 命名也不会发生


# ============================================================
# SSE 通道保护
# ============================================================


class TestStreamProtection:
    """通道级保护（超时 / 断连 / 异常兜底）测试。"""

    def test_timeout_emits_error_and_done(self, monkeypatch: pytest.MonkeyPatch):
        """请求级超时：第一个事件即超时 → error + done 并终止。"""
        service, _, _, _, _ = _build_service()
        monkeypatch.setattr(settings.ai.llm, "chat_request_timeout_seconds", -1)
        stream = iter([{"type": "token", "content": "x"}])
        events = list(service._stream_with_protection(stream, conversation_id=1, disconnect_checker=None))
        assert [e["type"] for e in events] == [
            AssistantEventType.ERROR.mark,
            AssistantEventType.DONE.mark,
        ]
        assert events[-1]["message_id"] is None

    def test_disconnect_silently_stops(self):
        """客户端断连检测命中：静默终止，不再透出事件。"""
        service, _, _, _, _ = _build_service()
        stream = iter([{"type": "token", "content": "x"}])
        events = list(service._stream_with_protection(stream, conversation_id=1, disconnect_checker=lambda: True))
        assert events == []

    def test_unexpected_exception_falls_back(self):
        """事件流抛不可预期异常：兜底为 error + done，不中断响应。"""
        service, _, _, _, _ = _build_service()

        def _broken_stream():
            yield {"type": "token", "content": "前"}
            raise RuntimeError("boom")

        events = list(service._stream_with_protection(_broken_stream(), conversation_id=1, disconnect_checker=None))
        assert [e["type"] for e in events][-2:] == [
            AssistantEventType.ERROR.mark,
            AssistantEventType.DONE.mark,
        ]


# ============================================================
# 收尾辅助方法
# ============================================================


class TestNavigateReplyBuilder:
    """_build_navigate_reply 兜底文案测试。"""

    def test_faq_hit_returns_standard_answer(self):
        """FAQ 命中真实资产关键词：返回标准答案。"""
        service, _, _, _, _ = _build_service()
        reply = service._build_navigate_reply("怎么添加用户", {"path": "/users"})
        assert "用户管理" in reply

    def test_known_path_uses_catalog_description(self):
        """未命中 FAQ 但路径在入口目录：按目录描述生成引导语。"""
        service, _, _, _, _ = _build_service()
        reply = service._build_navigate_reply("随便问问", {"path": "/users"})
        assert "已为你打开" in reply
        assert "用户列表、新增、编辑与启用停用" in reply

    def test_unknown_path_uses_generic_description(self):
        """路径不在入口目录：退化为「相关页面」。"""
        service, _, _, _, _ = _build_service()
        reply = service._build_navigate_reply("随便问问", {"path": "/no-such"})
        assert "相关页面" in reply

    def test_empty_path_returns_apology(self):
        """无路径：返回抱歉提示。"""
        service, _, _, _, _ = _build_service()
        reply = service._build_navigate_reply("随便问问", {})
        assert "抱歉" in reply


class TestMaybeRename:
    """会话自动命名测试。"""

    def test_skip_when_title_already_set(self):
        """已有标题：不再调 LLM 命名。"""
        llm = FakeLLM()
        service, conv_repo, _, _, _ = _build_service(llm)
        conv = _new_conversation(conv_repo, 7)
        conv.title = "已命名"
        service._maybe_rename(conv, "问题", "回答")
        assert llm.chat_calls == 0

    def test_rename_writes_title(self):
        """无标题且 LLM 返回标题：写库并同步内存对象。"""
        llm = FakeLLM(chat_content="用户咨询公告")
        service, conv_repo, _, _, _ = _build_service(llm)
        conv = _new_conversation(conv_repo, 7)
        service._maybe_rename(conv, "怎么发公告", "进入公告管理")
        assert conv.title == "用户咨询公告"
        assert conv_repo.title_updates == [(conv.id, "用户咨询公告")]

    def test_empty_title_skips(self):
        """LLM 返回空串：不写库。"""
        llm = FakeLLM(chat_content="")
        service, conv_repo, _, _, _ = _build_service(llm)
        conv = _new_conversation(conv_repo, 7)
        service._maybe_rename(conv, "问题", "回答")
        assert conv.title is None
        assert conv_repo.title_updates == []

    def test_llm_error_swallowed(self):
        """LLM 命名异常：静默吞掉，不影响主流程。"""
        llm = FakeLLM(chat_error=ExternalServiceException(message="命名失败"))
        service, conv_repo, _, _, _ = _build_service(llm)
        conv = _new_conversation(conv_repo, 7)
        service._maybe_rename(conv, "问题", "回答")  # 不应抛
        assert conv.title is None


class TestMaybeConsolidateProfile:
    """长期记忆抽取节流测试。"""

    def _conv_with_messages(self, msg_repo: FakeMessageRepo, count: int) -> int:
        for i in range(count):
            msg_repo.add_message(999, "user" if i % 2 == 0 else "assistant", f"内容{i}")
        return 999

    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch):
        """长期记忆开关默认关闭：直接跳过。"""
        service, _, msg_repo, _, _ = _build_service()
        conv = AssistantConversationEntity(id=999, user_id=7)
        service._maybe_consolidate_profile(conv)  # 不抛
        assert msg_repo.count_by_conversation(999) == 0

    def test_trigger_only_on_interval_multiple(self, monkeypatch: pytest.MonkeyPatch):
        """开启后：消息数为间隔整数倍才触发抽取；其余静默跳过。"""
        monkeypatch.setattr(settings.ai.memory.long_term, "enabled", True)
        monkeypatch.setattr(settings.ai.memory.long_term, "consolidate_interval", 5)
        service, _, msg_repo, _, _ = _build_service()
        spy = MagicMock()
        service._memory_facade.consolidate_user_profile = spy

        conv = AssistantConversationEntity(id=999, user_id=7)
        # 3 条：不是 5 的倍数 → 不触发
        self._conv_with_messages(msg_repo, 3)
        service._maybe_consolidate_profile(conv)
        spy.assert_not_called()
        # 再补 2 条共 5 条：触发一次
        for i in range(3, 5):
            msg_repo.add_message(999, "user", f"补{i}")
        service._maybe_consolidate_profile(conv)
        spy.assert_called_once_with(7, 999)

    def test_consolidate_error_swallowed(self, monkeypatch: pytest.MonkeyPatch):
        """抽取失败：仅记日志，不影响主流程。"""
        monkeypatch.setattr(settings.ai.memory.long_term, "enabled", True)
        monkeypatch.setattr(settings.ai.memory.long_term, "consolidate_interval", 1)
        service, _, msg_repo, _, _ = _build_service()
        service._memory_facade.consolidate_user_profile = MagicMock(side_effect=RuntimeError("抽取炸了"))
        conv = AssistantConversationEntity(id=999, user_id=7)
        msg_repo.add_message(999, "user", "唯一一条")
        service._maybe_consolidate_profile(conv)  # 不抛


class TestFinishRound:
    """轮次收尾（_finish_round）测试：DONE 先行、重活失败静默。"""

    def test_done_emitted_before_heavy_lifting_and_failure_swallowed(self):
        """滚动摘要压缩失败仅记日志：DONE 照常下发、助手消息照常落库。"""
        llm = FakeLLM()
        service, conv_repo, msg_repo, _, _ = _build_service(llm)
        conv = _new_conversation(conv_repo, 7)
        # 让收尾重活（滚动摘要）抛错，验证被兜底吞掉
        service._memory_facade.roll_summary = MagicMock(side_effect=RuntimeError("压缩炸了"))
        events = list(service._finish_round(conv, "问题", "最终回复"))
        assert events[0]["type"] == AssistantEventType.DONE.mark
        assert events[0]["message_id"] is not None
        # 助手回复已落库
        contents = [m.content for m in msg_repo._items]
        assert "最终回复" in contents


class TestAuditNavigate:
    """跳转审计（失败静默）测试。"""

    def test_audit_with_varied_operator(self):
        """operator 缺省 / ip 非法类型：均不抛异常（审计写库已在 conftest 降级 no-op）。"""
        service, _, _, _, _ = _build_service()
        user = _make_user()
        service._audit_navigate(user, 1, {"path": "/users"}, operator=None)
        service._audit_navigate(user, 1, {"path": "/users"}, operator={"ip_address": 12345})
        service._audit_navigate(user, 1, {"path": "/users"}, operator={"ip_address": "1.2.3.4"})


class TestMcpRegistryBranch:
    """默认工具注册表的 MCP 开关分支测试。"""

    def test_mcp_enabled_registers_source(self, monkeypatch: pytest.MonkeyPatch):
        """mcp_enabled=True 时装配 MCP 工具源（当前为空实现）。"""
        monkeypatch.setattr(settings.ai.tools, "mcp_enabled", True)
        service, _, _, _, _ = _build_service()
        names = service._tool_registry.names()
        assert "navigate" in names  # 内置工具照常注册
