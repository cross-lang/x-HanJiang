#!/usr/bin/env python3
"""L1 用户长期记忆：抽象接口、空实现、数据库实现与装配工厂。

读路径 load_user_context：取用户档案注入系统提示词（每轮对话，由
MemoryFacade 统一拉取后经 ctx 喂给 L0）；
写路径 consolidate：从最近对话中抽取并沉淀档案（对话收尾按间隔触发）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

import yaml

from src.assistant.memories.ports import MessageRepository, UserProfileRepository
from src.core.config import settings
from src.core.logger import logger
from src.infras.llm import LLMProvider, get_llm_provider
from src.utils.helpers import find_project_root


class UserLongTermMemory(ABC):
    """用户长期记忆提供者（第 1 层抽象接口）。

    读路径 load_user_context：取用户档案注入系统提示词（每轮对话调用）；
    写路径 consolidate：从最近对话中抽取并沉淀档案（对话收尾按间隔触发）。

    后续接入方式：
        1. 新增 user_profile 表（用户长期偏好 / 关注点）
        2. 实现子类读取该表并返回档案文本
        3. 替换装配层中的 NullUserLongTermMemory 为真实实现
    """

    @abstractmethod
    def load_user_context(self, user_id: int) -> str:
        """返回注入系统提示词的『用户档案』文本。

        Args:
            user_id: 用户ID

        Returns:
            str: 档案文本；未接入长期记忆时返回空串
        """

    @abstractmethod
    def consolidate(self, user_id: int, conversation_id: int) -> None:
        """从最近对话抽取并更新用户档案（对话收尾时触发）。

        Args:
            user_id: 用户ID
            conversation_id: 会话ID（取最近对话原文用）
        """


class NullUserLongTermMemory(UserLongTermMemory):
    """长期记忆空实现（占位）。

    第 1 层未启用时使用，读路径返回空串、写路径直接跳过，
    保证上层提示词组装与收尾逻辑不变。
    """

    def load_user_context(self, user_id: int) -> str:
        return ""

    def consolidate(self, user_id: int, conversation_id: int) -> None:
        return None


class DbUserLongTermMemory(UserLongTermMemory):
    """基于数据库的用户长期记忆实现。

    读路径 load_user_context：按 user_id 查 assistant_user_profiles 表，
    返回 profile 文本供 L0 注入系统提示词；
    写路径 consolidate：取最近对话原文 → 拼接旧档案 → LLM 抽取 → upsert。

    依赖端口（依赖倒置，不认识 SQLAlchemy）：
        - profile_repository: UserProfileRepository 端口（档案读写）
        - message_repository: MessageRepository 端口（取最近对话）
        - llm_provider_getter: LLM 获取器（抽取调用，懒加载）

    抽取 prompt 模板：src/templates/assistant_templates/user_profile_extract.yaml，
    懒加载缓存，结构同 assistant_prompt.yaml。
    """

    def __init__(
        self,
        profile_repository: UserProfileRepository,
        message_repository: MessageRepository,
        llm_provider_getter: Callable[[], LLMProvider],
        extract_prompt_path: Path | None = None,
    ) -> None:
        """初始化长期记忆实现。

        Args:
            profile_repository: 用户档案存储端口
            message_repository: 消息存储端口（取最近对话原文）
            llm_provider_getter: LLM 获取器（抽取调用，懒加载）
            extract_prompt_path: 抽取 prompt 模板路径（缺省使用默认路径）
        """
        self._profile_repository: UserProfileRepository = profile_repository
        self._message_repository: MessageRepository = message_repository
        self._get_llm: Callable[[], LLMProvider] = llm_provider_getter
        self._extract_prompt_path: Path = extract_prompt_path or (
            find_project_root() / "src" / "templates" / "assistant_templates" / "user_profile_extract.yaml"
        )
        self._extract_prompt_template: str | None = None

    def load_user_context(self, user_id: int) -> str:
        """查表返回用户档案文本（无记录返回空串）。

        Args:
            user_id: 用户ID

        Returns:
            str: 档案文本；无记录返回空串
        """
        entity = self._profile_repository.get_by_user(user_id)
        if entity is None:
            return ""
        profile = getattr(entity, "profile", None)
        return profile if profile else ""

    def consolidate(self, user_id: int, conversation_id: int) -> None:
        """从最近对话抽取并更新用户档案。

        流程：取最近 N 条对话 → 读旧档案 → LLM 抽取 → upsert 写回。
        失败仅记日志（尽力而为，不阻断主流程）。

        Args:
            user_id: 用户ID
            conversation_id: 会话ID
        """
        long_term_cfg = settings.ai.memory.long_term
        if not long_term_cfg.enabled:
            return
        # 1. 取最近对话原文（限制条数避免 prompt 过长）
        recent = self._message_repository.list_by_conversation(
            conversation_id, limit=long_term_cfg.consolidate_interval * 2
        )
        if not recent:
            return
        # 2. 拼接对话文本与旧档案
        dialog_text = "\n".join(f"{msg.role}: {msg.content}" for msg in recent)
        old_entity = self._profile_repository.get_by_user(user_id)
        old_profile = getattr(old_entity, "profile", "") or ""
        old_version = getattr(old_entity, "version", 0) or 0
        # 3. 加载抽取 prompt 模板并填充
        template = self._load_extract_prompt_template()
        prompt = template.format(
            old_profile=old_profile or "（暂无）",
            recent_dialog=dialog_text,
            max_profile_tokens=long_term_cfg.max_profile_tokens,
        )
        # 4. 调 LLM 抽取新档案
        messages: list[dict[str, str]] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请抽取用户档案。"},
        ]
        result = self._get_llm().chat(
            messages=messages,
            temperature=0.3,
            max_tokens=long_term_cfg.max_profile_tokens,
        )
        new_profile = (result.content or "").strip()
        if not new_profile or new_profile == old_profile:
            return
        # 5. upsert 写回（带版本号递增）
        self._profile_repository.upsert(user_id, new_profile, old_version)
        logger.info(f"AI 助手长期记忆抽取：user={user_id} version={old_version + 1}")

    def _load_extract_prompt_template(self) -> str:
        """加载抽取 prompt 模板（懒加载缓存）。

        Returns:
            str: 抽取 prompt 模板（含占位符）

        Raises:
            ValueError: 模板文件缺失或结构不合法
        """
        if self._extract_prompt_template is not None:
            return self._extract_prompt_template
        if not self._extract_prompt_path.exists():
            raise ValueError(f"用户档案抽取模板不存在: {self._extract_prompt_path}")
        try:
            raw: object = yaml.safe_load(self._extract_prompt_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"用户档案抽取模板 YAML 解析失败: {self._extract_prompt_path}: {exc}") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("system_prompt"), str):
            raise ValueError(f"用户档案抽取模板缺少 system_prompt 字段: {self._extract_prompt_path}")
        template: str = raw["system_prompt"]
        required = ("{old_profile}", "{recent_dialog}", "{max_profile_tokens}")
        missing = [name for name in required if name not in template]
        if missing:
            raise ValueError(f"用户档案抽取模板缺少必需占位符 {missing}: {self._extract_prompt_path}")
        self._extract_prompt_template = template
        return template


# ============================================================
# 工厂
# ============================================================


def build_user_long_term_memory(
    profile_repository: UserProfileRepository,
    message_repository: MessageRepository,
    llm_provider_getter: Callable[[], LLMProvider] | None = None,
) -> UserLongTermMemory:
    """按配置创建长期记忆实现实例。

    Args:
        profile_repository: 用户档案存储端口
        message_repository: 消息存储端口
        llm_provider_getter: LLM 获取器（缺省使用全局懒加载工厂）

    Returns:
        UserLongTermMemory: 配置开启时返回 DbUserLongTermMemory，否则返回空实现
    """
    if not settings.ai.memory.long_term.enabled:
        return NullUserLongTermMemory()
    return DbUserLongTermMemory(
        profile_repository=profile_repository,
        message_repository=message_repository,
        llm_provider_getter=llm_provider_getter or get_llm_provider,
    )
