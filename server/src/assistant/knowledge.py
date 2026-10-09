#!/usr/bin/env python3
"""静态知识库：FAQ 操作手册与系统提示词组装。

职责：
    - FAQ 操作手册：数据模型（FaqItem）+ 加载校验（load_assistant_faq）
      数据文件 server/src/templates/assistant_templates/assistant_faq.yaml
    - 系统提示词组装：将入口清单（ASSISTANT_ENTRY_CATALOG）、FAQ 操作手册
      与用户档案（记忆第 1 层注入点）组装为系统提示词，注入对话上下文
    - 入口清单与 FAQ 当前来自常量/数据文件（静态维护）；后续可替换为从菜单表 /
      数据表动态生成，本类只依赖数据源，替换数据源不影响上层

知识分层（第 1 级方案）：
    - 入口清单：回答「系统有哪些页面、如何跳转」（服务 navigate 工具）
    - FAQ 操作手册：回答「具体操作怎么做」（分步步骤，来自系统真实流程）
    - match_faq() 做确定性关键词召回：命中当前问题对应 FAQ 时，
      将标准答案注入【优先参考】块，并要求模型以该答案为准组织回复，
      从约束层压制「答非所问 / 编造操作步骤」

说明：
    - RAG 注入链路已就绪（SystemPromptLayer → retriever_context → rag_block），
      当前为 NullRetriever 空实现返回空串，待接入向量检索
    - 用户档案（第 1 层长期记忆）与 RAG 补充知识均为「本轮动态内容」，由
      L0 层（SystemPromptLayer）取好后以参数传入，本类不依赖记忆层 / 检索层，
      只做静态模板渲染，零 I/O
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.constants.assistant import ASSISTANT_ENTRY_CATALOG
from src.utils.helpers import find_project_root


# ============================================================
# FAQ 数据模型与加载器
# ============================================================


@dataclass(frozen=True)
class FaqItem:
    """一条 FAQ：常见问法 → 分步操作答案。

    Attributes:
        id: 条目标识（供测试与日志定位，必须唯一）
        keywords: 同义问法关键词（对用户问题子串匹配，命中任一即召回）
        question: 标准问法（展示给模型）
        answer: 分步操作答案（编号步骤，来自系统真实流程）
        entry_path: 关联入口路径（回答末尾可引导跳转；空 = 无需跳转）
    """

    id: str
    keywords: tuple[str, ...]
    question: str
    answer: str
    entry_path: str


def default_faq_path() -> Path:
    """返回默认 FAQ 数据文件路径。

    Returns:
        Path: server/src/templates/assistant_templates/assistant_faq.yaml 的绝对路径
    """
    return find_project_root() / "src" / "templates" / "assistant_templates" / "assistant_faq.yaml"


def load_assistant_faq(path: Path | None = None) -> tuple[FaqItem, ...]:
    """加载并校验 FAQ 内容资产。

    Args:
        path: 数据文件路径；缺省使用 default_faq_path()

    Returns:
        tuple[FaqItem, ...]: 按文件顺序排列的 FAQ 条目（顺序即匹配优先级）

    Raises:
        ValueError: 文件缺失、YAML 解析失败或结构校验失败（含 id 重复、
            entry_path 不在入口目录、必填字段缺失/类型错误、条目为空）
    """
    faq_path = path if path is not None else default_faq_path()
    if not faq_path.exists():
        raise ValueError(f"FAQ 数据文件不存在: {faq_path}")
    try:
        raw: object = yaml.safe_load(faq_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"FAQ 数据文件 YAML 解析失败: {faq_path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("faq"), list):
        raise ValueError(f"FAQ 数据文件结构非法（顶层需为 dict 且含 faq 列表）: {faq_path}")

    faq_list: list[object] = raw["faq"]
    items: list[FaqItem] = []
    seen_ids: set[str] = set()
    valid_paths: set[str] = {item["path"] for item in ASSISTANT_ENTRY_CATALOG}
    for index, entry in enumerate(faq_list):
        if not isinstance(entry, dict):
            raise ValueError(f"FAQ 第 {index + 1} 条不是对象: {faq_path}")
        item_id = entry.get("id")
        keywords = entry.get("keywords")
        question = entry.get("question")
        answer = entry.get("answer")
        entry_path = entry.get("entry_path", "")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(f"FAQ 第 {index + 1} 条 id 缺失或非字符串: {faq_path}")
        if (
            not isinstance(keywords, list)
            or not keywords
            or not all(isinstance(keyword, str) and keyword for keyword in keywords)
        ):
            raise ValueError(f"FAQ[{item_id}] keywords 缺失或非非空字符串列表: {faq_path}")
        if not isinstance(question, str) or not question:
            raise ValueError(f"FAQ[{item_id}] question 缺失或非字符串: {faq_path}")
        if not isinstance(answer, str) or not answer:
            raise ValueError(f"FAQ[{item_id}] answer 缺失或非字符串: {faq_path}")
        if not isinstance(entry_path, str) or (entry_path and entry_path not in valid_paths):
            raise ValueError(f"FAQ[{item_id}] entry_path 非法（需为入口目录路由或留空）: {faq_path}")
        if item_id in seen_ids:
            raise ValueError(f"FAQ id 重复: {item_id}")
        seen_ids.add(item_id)
        items.append(
            FaqItem(
                id=item_id,
                keywords=tuple(keywords),
                question=question,
                answer=answer,
                entry_path=entry_path,
            )
        )
    if not items:
        raise ValueError(f"FAQ 数据为空: {faq_path}")
    return tuple(items)


# ============================================================
# 系统提示词数据模型与加载器
# ============================================================


@dataclass(frozen=True)
class PromptTemplate:
    """系统提示词模板加载结果。

    Attributes:
        system_prompt: 系统提示词模板（含占位符）
        faq_block_template: 命中 FAQ 的【优先参考】块模板
    """

    system_prompt: str
    faq_block_template: str


def default_prompt_path() -> Path:
    """返回默认系统提示词模板文件路径。

    Returns:
        Path: server/src/templates/assistant_templates/assistant_prompt.yaml 的绝对路径
    """
    return find_project_root() / "src" / "templates" / "assistant_templates" / "assistant_prompt.yaml"


def load_prompt_template(path: Path | None = None) -> PromptTemplate:
    """加载系统提示词模板并校验结构。

    Args:
        path: 系统提示词模板文件路径；缺省使用 default_prompt_path()

    Returns:
        PromptTemplate: 含 system_prompt 和 faq_block_template 的加载结果

    Raises:
        ValueError: 模板文件缺失、结构不合法或缺少必需占位符
    """
    prompt_path = path if path is not None else default_prompt_path()
    if not prompt_path.exists():
        raise ValueError(f"系统提示词模板不存在: {prompt_path}")
    try:
        raw: object = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"系统提示词模板 YAML 解析失败: {prompt_path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("system_prompt"), str):
        raise ValueError(f"系统提示词模板缺少 system_prompt 字段: {prompt_path}")
    template: str = raw["system_prompt"]
    required = ("{entries_block}", "{user_block}", "{faq_block}", "{rag_block}")
    missing = [name for name in required if name not in template]
    if missing:
        raise ValueError(f"系统提示词模板缺少必需占位符 {missing}: {prompt_path}")
    faq_tpl = raw.get("faq_block_template")
    if not isinstance(faq_tpl, str) or not faq_tpl:
        raise ValueError(f"系统提示词模板缺少 faq_block_template 字段: {prompt_path}")
    return PromptTemplate(system_prompt=template, faq_block_template=faq_tpl)


# ============================================================
# 系统提示词组装器
# ============================================================


class SystemPromptBuilder:
    """系统提示词组装器（纯静态渲染：输入本轮内容，输出提示词）。

    Attributes:
        _faq_items: FAQ 操作手册条目（加载自数据文件，顺序即匹配优先级）
        _tpl: 系统提示词模板加载结果（含 system_prompt 和 faq_block_template）
    """

    def __init__(
        self,
        faq_path: Path | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        """初始化知识库。

        Args:
            faq_path: FAQ 数据文件路径（缺省使用默认路径）
            prompt_path: 系统提示词模板路径（缺省使用默认路径）
        """
        self._faq_items: tuple[FaqItem, ...] = load_assistant_faq(faq_path)
        self._tpl: PromptTemplate = load_prompt_template(prompt_path)

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

    def _build_entries_block(self, user_permissions: set[str] | None) -> str:
        """按用户权限过滤系统入口路由表并渲染为多行列表文本。

        过滤规则：
            - None 或含 "*"：返回全量（兼容测试 / 超管通配）
            - 否则：只保留 permission==""（登录即可访问）或 permission 在集合中的入口

        Args:
            user_permissions: 用户权限码集合

        Returns:
            str: 渲染后的系统入口路由表文本，每行格式「- 标题（路径）：用途说明」
        """
        if user_permissions is None or "*" in user_permissions:
            entries = ASSISTANT_ENTRY_CATALOG
        else:
            entries = tuple(
                item for item in ASSISTANT_ENTRY_CATALOG
                if not item["permission"] or item["permission"] in user_permissions
            )
        return "\n".join(
            f"- {item['title']}（{item['path']}）：{item['description']}"
            for item in entries
        )

    def build_system_prompt(
        self,
        user_context: str = "",
        retriever_context: str = "",
        user_question: str = "",
        user_permissions: set[str] | None = None,
    ) -> str:
        """组装系统提示词。

        Args:
            user_context: 用户档案文本（第 1 层长期记忆内容，由 L0 层读取后
                传入；空串表示无档案，模板中给出通用回答提示）
            retriever_context: 检索补充知识（RAG 预留，未启用时为空串）
            user_question: 本轮用户提问（用于命中 FAQ，为空则跳过）
            user_permissions: 当前用户权限码集合，用于过滤入口清单；
                None 表示不过滤（全量，兼容测试/无权限场景）；
                含 "*" 表示超级管理员通配，保留全量；
                空集或部分集合则只保留 permission=="" 或 permission in 集合 的入口

        Returns:
            str: 完整系统提示词，包含系统入口路由表、用户档案、补充知识、FAQ 个块。
        """
        # 入口清单块：按用户权限过滤后渲染为多行列表
        entries_block = self._build_entries_block(user_permissions)
        # 用户档案块：L1 长期记忆内容；空则给通用兜底，保证模板占位总有值
        user_block = user_context if user_context else "（暂无，按通用规则回答）"
        # 补充知识块：RAG 检索结果；无内容时为空串，模板对应段直接省略
        rag_block = f"\n【补充知识】\n{retriever_context}" if retriever_context else ""
        # 按本轮问题做确定性关键词召回（数据文件顺序即优先级）
        hit = self.match_faq(user_question) if user_question else None
        faq_block = ""
        # 命中 FAQ 则用模板渲染【优先参考】块，约束模型以标准答案为准组织回复
        if hit is not None:
            faq_block = self._tpl.faq_block_template.format(
                hit_question=hit.question,
                hit_answer=hit.answer,
                hit_entry_path=hit.entry_path or "无需跳转",
            )
        # 用四个块填充模板占位符，输出完整系统提示词
        return self._tpl.system_prompt.format(
            entries_block=entries_block,
            user_block=user_block,
            faq_block=faq_block,
            rag_block=rag_block,
        )

