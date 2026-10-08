#!/usr/bin/env python3
"""静态知识库：系统提示词与入口清单组装。

职责：
    - 将系统入口清单（ASSISTANT_ENTRY_CATALOG）、FAQ 操作手册（数据文件
      server/templates/assistant_templates/assistant_faq.yaml，经 src.assistant.faq 加载）
      与用户档案（记忆第 1 层注入点）组装为系统提示词，注入对话上下文
    - 入口清单与 FAQ 当前来自常量（静态维护）；后续可替换为从菜单表 /
      数据表动态生成，本类只依赖数据源，替换数据源不影响上层

知识分层（第 1 级方案）：
    - 入口清单：回答「系统有哪些页面、如何跳转」（服务 navigate 工具）
    - FAQ 操作手册：回答「具体操作怎么做」（分步步骤，来自系统真实流程）
    - match_faq() 做确定性关键词召回：命中当前问题对应 FAQ 时，
      将标准答案注入【优先参考】块，并要求模型以该答案为准组织回复，
      从约束层压制「答非所问 / 编造操作步骤」

说明：
    - 不引入 RAG：知识以提示词注入为主；retriever_context 参数预留 RAG 注入位
    - 用户档案通过 UserMemoryProvider 注入（第 1 层长期记忆，当前为空实现）
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.assistant.faq import FaqItem, load_assistant_faq
from src.assistant.memory import UserMemoryProvider
from src.constants.assistant import ASSISTANT_ENTRY_CATALOG
from src.utils.helpers import find_project_root


class SystemPromptBuilder:
    """系统提示词组装器。

    Attributes:
        _user_memory: 用户长期记忆提供者（第 1 层注入点）
        _faq_items: FAQ 操作手册条目（加载自数据文件，顺序即匹配优先级）
        _prompt_path: 系统提示词模板路径（默认 templates/assistant_templates/assistant_prompt.yaml）
        _prompt_template: 系统提示词模板缓存（懒加载）
        _faq_block_template: 命中 FAQ 的【优先参考】块模板
    """

    def __init__(
        self,
        user_memory: UserMemoryProvider,
        faq_path: Path | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        """初始化知识库。

        Args:
            user_memory: 用户长期记忆提供者
            faq_path: FAQ 数据文件路径（缺省使用默认路径）
            prompt_path: 系统提示词模板路径（缺省使用默认路径）
        """
        self._user_memory: UserMemoryProvider = user_memory
        self._faq_items: tuple[FaqItem, ...] = load_assistant_faq(faq_path)
        self._prompt_path: Path = prompt_path or (
            find_project_root() / "templates" / "assistant_templates" / "assistant_prompt.yaml"
        )
        self._prompt_template: str | None = None
        self._faq_block_template: str = ""

    def match_faq(self, question: str) -> FaqItem | None:
        """按关键词召回命中当前问题的 FAQ（确定性匹配，可单测）。

        匹配规则：对问题原文按加载顺序（数据文件顺序 = 优先级）做关键词
        子串匹配，命中任一关键词即返回该条目。

        Args:
            question: 用户本轮提问原文

        Returns:
            FaqItem | None: 命中的 FAQ 条目；未命中返回 None
        """
        normalized = question.strip()
        if not normalized:
            return None
        for item in self._faq_items:
            for keyword in item.keywords:
                if keyword in normalized:
                    return item
        return None

    def build_system_prompt(
        self,
        user_id: int,
        retriever_context: str = "",
        user_question: str = "",
    ) -> str:
        """组装系统提示词。

        Args:
            user_id: 当前用户ID（用于注入用户档案）
            retriever_context: 检索补充知识（RAG 预留，未启用时为空串）
            user_question: 本轮用户提问（用于命中 FAQ，为空则跳过）

        Returns:
            str: 完整系统提示词
        """
        entries_block = "\n".join(
            f"- {item['title']}（{item['path']}）：{item['description']}"
            for item in ASSISTANT_ENTRY_CATALOG
        )
        user_context = self._user_memory.load_user_context(user_id)
        user_block = user_context if user_context else "（暂无，按通用规则回答）"
        rag_block = f"\n【补充知识】\n{retriever_context}" if retriever_context else ""
        hit = self.match_faq(user_question) if user_question else None
        faq_block = ""
        if hit is not None:
            faq_block = self._faq_block_template.format(
                hit_question=hit.question,
                hit_answer=hit.answer,
                hit_entry_path=hit.entry_path or "无需跳转",
            )
        template = self._load_prompt_template()
        return template.format(
            entries_block=entries_block,
            user_block=user_block,
            faq_block=faq_block,
            rag_block=rag_block,
        )

    def _load_prompt_template(self) -> str:
        """加载系统提示词模板（懒加载缓存 + 结构校验）。

        Returns:
            str: 系统提示词模板（含占位符）

        Raises:
            ValueError: 模板文件缺失、结构不合法或缺少必需占位符
        """
        if self._prompt_template is not None:
            return self._prompt_template
        if not self._prompt_path.exists():
            raise ValueError(f"系统提示词模板不存在: {self._prompt_path}")
        try:
            raw: object = yaml.safe_load(self._prompt_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"系统提示词模板 YAML 解析失败: {self._prompt_path}: {exc}") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("system_prompt"), str):
            raise ValueError(f"系统提示词模板缺少 system_prompt 字段: {self._prompt_path}")
        template: str = raw["system_prompt"]
        required = ("{entries_block}", "{user_block}", "{faq_block}", "{rag_block}")
        missing = [name for name in required if name not in template]
        if missing:
            raise ValueError(f"系统提示词模板缺少必需占位符 {missing}: {self._prompt_path}")
        faq_tpl = raw.get("faq_block_template")
        if not isinstance(faq_tpl, str) or not faq_tpl:
            raise ValueError(f"系统提示词模板缺少 faq_block_template 字段: {self._prompt_path}")
        self._faq_block_template = faq_tpl
        self._prompt_template = template
        return template
