#!/usr/bin/env python3
"""第 2 层滚动摘要记忆（SummaryMemoryLayer）单元测试。

测试 src/assistant/memories/summary.py：
    - contribute（读路径）：有摘要注入「历史摘要」system 消息并扣预算；无摘要跳过
    - consolidate（写路径）：记忆开关关闭 / 未超保留窗口 / 窗口外无消息时跳过；
      正常折入时 LLM 压缩 → 更新摘要 → 删除原文 → 同事务提交

LLM 的 summarize 调用一律用内存 fake 替身，不触网；settings 用 mock 隔离。
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

from src.assistant.memories.base import MemoryContext
from src.assistant.memories.summary import SummaryMemoryLayer
from src.infras.llm import LLMProvider
from src.utils.text import estimate_tokens

# ============================================================
# 测试替身
# ============================================================


@dataclass
class _FakeConversation:
    """会话实体最小替身（仅含摘要层用到的字段）。"""

    id: int
    summary: str | None = None


@dataclass
class _FakeMessage:
    """消息实体最小替身。"""

    id: int
    role: str
    content: str


class _FakeConversationRepo:
    """会话仓储替身：记录 update_summary / commit 调用。"""

    def __init__(self) -> None:
        self.updated: list[tuple[int, str]] = []
        self.commits: int = 0

    def update_summary(self, conversation_id: int, summary: str) -> None:
        self.updated.append((conversation_id, summary))

    def commit(self) -> None:
        self.commits += 1


class _FakeMessageRepo:
    """消息仓储替身：count / list_oldest / delete 均可脚本化。"""

    def __init__(
        self,
        total: int = 0,
        oldest_outside: list[_FakeMessage] | None = None,
    ) -> None:
        self._total = total
        self._oldest = oldest_outside or []
        self.deleted_ids: list[list[int]] = []

    def count_by_conversation(self, conversation_id: int) -> int:
        return self._total

    def list_oldest_outside_window(self, conversation_id: int, keep_count: int, limit: int = 10):
        return list(self._oldest)

    def delete_by_ids(self, message_ids: list[int]) -> None:
        self.deleted_ids.append(list(message_ids))


class _FakeLLM(LLMProvider):
    """LLM 替身：summarize 返回固定摘要并记录调用入参。"""

    def __init__(self, summary: str = "压缩后的摘要") -> None:
        self._summary = summary
        self.summarized_texts: list[str] = []

    def chat_stream(self, messages, tools=None, temperature=None, max_tokens=None):
        raise NotImplementedError

    def chat(self, messages, tools=None, temperature=None, max_tokens=None):
        raise NotImplementedError

    def summarize(self, text: str) -> str:
        self.summarized_texts.append(text)
        return self._summary


def _make_layer(
    msg_repo: _FakeMessageRepo, llm: _FakeLLM | None = None
) -> tuple[SummaryMemoryLayer, _FakeConversationRepo]:
    """组装摘要层 + 两个仓储替身。"""
    conv_repo = _FakeConversationRepo()
    layer = SummaryMemoryLayer(
        conversation_repository=conv_repo,
        message_repository=msg_repo,
        llm_provider_getter=lambda: llm or _FakeLLM(),
    )
    return layer, conv_repo


# ============================================================
# contribute（读路径）
# ============================================================


class TestContribute:
    """历史摘要注入测试。"""

    def test_no_summary_skips(self):
        """无摘要：不注入任何消息、不扣预算。"""
        layer, _ = _make_layer(_FakeMessageRepo())
        ctx = MemoryContext(remaining_budget=1000)
        conv = _FakeConversation(id=1, summary=None)
        layer.contribute(ctx, conv, user_id=1, query="任意问题")
        assert ctx.messages == []
        assert ctx.remaining_budget == 1000

    def test_blank_summary_skips(self):
        """空串摘要视为无摘要，跳过。"""
        layer, _ = _make_layer(_FakeMessageRepo())
        ctx = MemoryContext(remaining_budget=1000)
        conv = _FakeConversation(id=1, summary="")
        layer.contribute(ctx, conv, user_id=1, query="任意问题")
        assert ctx.messages == []

    def test_summary_injected_and_charged(self):
        """有摘要：注入「历史摘要」system 消息，并按估算 token 扣预算。"""
        layer, _ = _make_layer(_FakeMessageRepo())
        ctx = MemoryContext(remaining_budget=1000)
        summary_text = "用户是管理员，关注公告管理"
        conv = _FakeConversation(id=1, summary=summary_text)
        layer.contribute(ctx, conv, user_id=1, query="任意问题")
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "system"
        assert ctx.messages[0]["content"] == f"历史摘要：{summary_text}"
        # 预算扣减额与估算 token 一致（不产生负预算）
        expected_charge = estimate_tokens(f"历史摘要：{summary_text}")
        assert ctx.remaining_budget == 1000 - expected_charge


# ============================================================
# consolidate（写路径）
# ============================================================


class TestConsolidate:
    """滚动摘要压缩触发与执行测试。"""

    def test_memory_disabled_skips(self):
        """记忆开关关闭：直接返回，不查消息、不调 LLM。"""
        msg_repo = _FakeMessageRepo(total=100)
        layer, conv_repo = _make_layer(msg_repo)
        with patch("src.assistant.memories.summary.settings") as mock_settings:
            mock_settings.ai.memory.enabled = False
            layer.consolidate(_FakeConversation(id=1))
        assert conv_repo.updated == []
        assert conv_repo.commits == 0

    def test_below_keep_window_skips(self):
        """消息总数未超过保留窗口（recent_raw_rounds × 2）：跳过压缩。"""
        # recent_raw_rounds=6 → keep_count=12；total=10 <= 12 不触发
        msg_repo = _FakeMessageRepo(total=10)
        layer, conv_repo = _make_layer(msg_repo, _FakeLLM())
        with patch("src.assistant.memories.summary.settings") as mock_settings:
            mock_settings.ai.memory.enabled = True
            mock_settings.ai.memory.recent_raw_rounds = 6
            layer.consolidate(_FakeConversation(id=1))
        assert conv_repo.updated == []

    def test_at_keep_window_boundary_skips(self):
        """总数恰好等于保留窗口：不触发（条件为 total <= keep_count）。"""
        msg_repo = _FakeMessageRepo(total=12)
        layer, conv_repo = _make_layer(msg_repo)
        with patch("src.assistant.memories.summary.settings") as mock_settings:
            mock_settings.ai.memory.enabled = True
            mock_settings.ai.memory.recent_raw_rounds = 6
            layer.consolidate(_FakeConversation(id=1))
        assert conv_repo.updated == []

    def test_no_old_messages_outside_window_skips(self):
        """超过窗口但仓储返回空窗口外消息：跳过。"""
        msg_repo = _FakeMessageRepo(total=15, oldest_outside=[])
        layer, conv_repo = _make_layer(msg_repo)
        with patch("src.assistant.memories.summary.settings") as mock_settings:
            mock_settings.ai.memory.enabled = True
            mock_settings.ai.memory.recent_raw_rounds = 6
            layer.consolidate(_FakeConversation(id=1))
        assert conv_repo.updated == []

    def test_normal_consolidate_updates_summary_and_deletes(self):
        """正常折入：旧消息 + LLM 摘要 → 更新摘要、同步内存对象、删原文、提交。"""
        old_messages = [
            _FakeMessage(id=10, role="user", content="怎么发公告"),
            _FakeMessage(id=11, role="assistant", content="点击公告管理"),
            _FakeMessage(id=12, role="user", content="怎么撤回"),
            _FakeMessage(id=13, role="assistant", content="在公告列表操作"),
        ]
        msg_repo = _FakeMessageRepo(total=20, oldest_outside=old_messages)
        llm = _FakeLLM(summary="用户咨询公告的发布与撤回")
        layer, conv_repo = _make_layer(msg_repo, llm)
        conv = _FakeConversation(id=7, summary=None)
        with patch("src.assistant.memories.summary.settings") as mock_settings:
            mock_settings.ai.memory.enabled = True
            mock_settings.ai.memory.recent_raw_rounds = 6
            layer.consolidate(conv)
        # LLM 压缩入参 = 窗口外消息拼接（无旧摘要时不含前缀）
        assert len(llm.summarized_texts) == 1
        assert "怎么发公告" in llm.summarized_texts[0]
        # 摘要落库 + 内存对象同步
        assert conv_repo.updated == [(7, "用户咨询公告的发布与撤回")]
        assert conv.summary == "用户咨询公告的发布与撤回"
        # 已折原文删除 + 一次提交
        assert msg_repo.deleted_ids == [[10, 11, 12, 13]]
        assert conv_repo.commits == 1

    def test_consolidate_joins_previous_summary(self):
        """已有旧摘要时：新旧文本拼接后再交给 LLM 压缩。"""
        old_messages = [_FakeMessage(id=20, role="user", content="新问题")]
        msg_repo = _FakeMessageRepo(total=15, oldest_outside=old_messages)
        llm = _FakeLLM(summary="合并后的摘要")
        layer, conv_repo = _make_layer(msg_repo, llm)
        conv = _FakeConversation(id=8, summary="旧摘要内容")
        with patch("src.assistant.memories.summary.settings") as mock_settings:
            mock_settings.ai.memory.enabled = True
            mock_settings.ai.memory.recent_raw_rounds = 6
            layer.consolidate(conv)
        combined = llm.summarized_texts[0]
        assert combined.startswith("旧摘要内容")
        assert "新问题" in combined
        assert conv_repo.updated == [(8, "合并后的摘要")]
