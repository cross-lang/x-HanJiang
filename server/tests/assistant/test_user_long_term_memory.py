#!/usr/bin/env python3
"""
AI 助手长期记忆（第 1 层）单元测试

测试 src/assistant/memories/long_term.py 中长期记忆相关逻辑：
    - NullUserLongTermMemory：空实现的读/写路径
    - DbUserLongTermMemory：基于数据库的实现（读路径 + 抽取写路径）
    - build_user_long_term_memory：工厂函数（开关分发）
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from src.assistant.memories import (
    DbUserLongTermMemory,
    NullUserLongTermMemory,
    build_user_long_term_memory,
)
from src.infras.llm import LLMChatResult, LLMProvider


# ============================================================
# 测试用 fakes
# ============================================================


@dataclass
class _FakeProfileEntity:
    """模拟档案实体（满足 UserProfileRepository.get_by_user 返回结构）。"""

    user_id: int
    profile: str | None = None
    version: int = 0


@dataclass
class _FakeMessageEntity:
    """模拟消息实体（满足 Message Protocol）。"""

    id: int
    role: str
    content: str


class _FakeProfileRepo:
    """档案仓储 fake（满足 UserProfileRepository Protocol）。"""

    def __init__(self, entity: _FakeProfileEntity | None = None) -> None:
        self._entity = entity
        self.upserted: list[tuple[int, str, int]] = []

    def get_by_user(self, user_id: int) -> _FakeProfileEntity | None:
        if self._entity is None:
            return None
        return self._entity

    def upsert(self, user_id: int, profile: str, version: int) -> None:
        new_version = version + 1
        self.upserted.append((user_id, profile, new_version))
        self._entity = _FakeProfileEntity(user_id=user_id, profile=profile, version=new_version)


class _FakeMessageRepo:
    """消息仓储 fake（满足 MessageRepository Protocol 的 list_by_conversation）。"""

    def __init__(self, messages: list[_FakeMessageEntity] | None = None) -> None:
        self._messages = messages or []

    def list_by_conversation(self, conversation_id: int, limit: int = 100) -> list[_FakeMessageEntity]:
        return self._messages[:limit]

    def count_by_conversation(self, conversation_id: int) -> int:
        return len(self._messages)


class _FakeLLMProvider(LLMProvider):
    """LLM 提供者 fake（chat 返回固定结果）。"""

    def __init__(self, content: str = "抽取结果") -> None:
        self._content = content

    def chat_stream(self, messages, tools=None, temperature=None, max_tokens=None):
        raise NotImplementedError

    def chat(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMChatResult:
        from openai.types.chat import ChatCompletionMessage

        return LLMChatResult(
            raw_message=ChatCompletionMessage(role="assistant", content=self._content),
            content=self._content,
            tool_calls=[],
        )

    def summarize(self, text: str) -> str:
        return self._content


def _make_db_memory(
    profile_repo: _FakeProfileRepo,
    message_repo: _FakeMessageRepo,
    llm: _FakeLLMProvider,
) -> DbUserLongTermMemory:
    """构造 DbUserLongTermMemory（绕过配置开关）。"""
    return DbUserLongTermMemory(
        profile_repository=profile_repo,
        message_repository=message_repo,
        llm_provider_getter=lambda: llm,
    )


# ============================================================
# NullUserLongTermMemory 测试
# ============================================================


class TestNullUserLongTermMemory:
    """空实现测试。"""

    def test_load_returns_empty(self):
        """读路径返回空串。"""
        memory = NullUserLongTermMemory()
        assert memory.load_user_context(1) == ""

    def test_consolidate_is_noop(self):
        """写路径不执行任何操作。"""
        memory = NullUserLongTermMemory()
        memory.consolidate(1, 100)  # 不应抛异常


# ============================================================
# DbUserLongTermMemory 读路径测试
# ============================================================


class TestDbLoadUserContext:
    """读路径测试。"""

    def test_no_profile_returns_empty(self):
        """无档案记录返回空串。"""
        repo = _FakeProfileRepo(entity=None)
        memory = _make_db_memory(repo, _FakeMessageRepo(), _FakeLLMProvider())
        assert memory.load_user_context(1) == ""

    def test_has_profile_returns_text(self):
        """有档案记录返回 profile 文本。"""
        repo = _FakeProfileRepo(entity=_FakeProfileEntity(user_id=1, profile="- 管理员", version=2))
        memory = _make_db_memory(repo, _FakeMessageRepo(), _FakeLLMProvider())
        assert memory.load_user_context(1) == "- 管理员"

    def test_empty_profile_returns_empty(self):
        """档案字段为 None 返回空串。"""
        repo = _FakeProfileRepo(entity=_FakeProfileEntity(user_id=1, profile=None, version=0))
        memory = _make_db_memory(repo, _FakeMessageRepo(), _FakeLLMProvider())
        assert memory.load_user_context(1) == ""


# ============================================================
# DbUserLongTermMemory 写路径测试
# ============================================================


class TestDbConsolidate:
    """抽取写路径测试。"""

    def test_disabled_skips(self):
        """配置开关关闭时跳过。"""
        repo = _FakeProfileRepo()
        memory = _make_db_memory(repo, _FakeMessageRepo(), _FakeLLMProvider())
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = False
            memory.consolidate(1, 100)
        assert repo.upserted == []

    def test_no_messages_skips(self):
        """无对话消息时跳过。"""
        repo = _FakeProfileRepo()
        memory = _make_db_memory(repo, _FakeMessageRepo([]), _FakeLLMProvider())
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = True
            mock_settings.ai.memory.long_term.consolidate_interval = 5
            mock_settings.ai.memory.long_term.max_profile_tokens = 500
            memory.consolidate(1, 100)
        assert repo.upserted == []

    def test_normal_extract_upserts(self):
        """正常流程：有对话 → LLM 抽取 → upsert 写回。"""
        messages = [
            _FakeMessageEntity(id=1, role="user", content="怎么发公告"),
            _FakeMessageEntity(id=2, role="assistant", content="点击公告管理"),
        ]
        repo = _FakeProfileRepo(entity=None)
        llm = _FakeLLMProvider(content="- 角色：管理员\n- 关注：公告管理")
        memory = _make_db_memory(repo, _FakeMessageRepo(messages), llm)
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = True
            mock_settings.ai.memory.long_term.consolidate_interval = 5
            mock_settings.ai.memory.long_term.max_profile_tokens = 500
            memory.consolidate(1, 100)
        assert len(repo.upserted) == 1
        user_id, profile, version = repo.upserted[0]
        assert user_id == 1
        assert "管理员" in profile
        assert version == 1  # 从 0 递增到 1

    def test_same_profile_skips_upsert(self):
        """LLM 输出与旧档案相同时不写回。"""
        old_profile = "- 角色：管理员"
        repo = _FakeProfileRepo(entity=_FakeProfileEntity(user_id=1, profile=old_profile, version=3))
        llm = _FakeLLMProvider(content=old_profile)
        messages = [_FakeMessageEntity(id=1, role="user", content="你好")]
        memory = _make_db_memory(repo, _FakeMessageRepo(messages), llm)
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = True
            mock_settings.ai.memory.long_term.consolidate_interval = 5
            mock_settings.ai.memory.long_term.max_profile_tokens = 500
            memory.consolidate(1, 100)
        assert repo.upserted == []

    def test_empty_llm_output_skips_upsert(self):
        """LLM 返回空串时不写回。"""
        repo = _FakeProfileRepo(entity=None)
        llm = _FakeLLMProvider(content="")
        messages = [_FakeMessageEntity(id=1, role="user", content="你好")]
        memory = _make_db_memory(repo, _FakeMessageRepo(messages), llm)
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = True
            mock_settings.ai.memory.long_term.consolidate_interval = 5
            mock_settings.ai.memory.long_term.max_profile_tokens = 500
            memory.consolidate(1, 100)
        assert repo.upserted == []


# ============================================================
# 工厂函数测试
# ============================================================


class TestBuildUserLongTermMemory:
    """工厂函数测试。"""

    def test_disabled_returns_null(self):
        """配置关闭时返回空实现。"""
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = False
            result = build_user_long_term_memory(
                profile_repository=_FakeProfileRepo(),
                message_repository=_FakeMessageRepo(),
            )
        assert isinstance(result, NullUserLongTermMemory)

    def test_enabled_returns_db(self):
        """配置开启时返回数据库实现。"""
        with patch("src.assistant.memories.long_term.settings") as mock_settings:
            mock_settings.ai.memory.long_term.enabled = True
            result = build_user_long_term_memory(
                profile_repository=_FakeProfileRepo(),
                message_repository=_FakeMessageRepo(),
            )
        assert isinstance(result, DbUserLongTermMemory)
