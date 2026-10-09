#!/usr/bin/env python3
"""AI 助手 FAQ 操作手册：数据模型与加载器。

FAQ 内容以数据文件（server/src/templates/assistant_templates/assistant_faq.yaml）承载，本模块只负责：
    - FaqItem：内容结构定义（数据模型，不承载业务逻辑）
    - load_assistant_faq()：加载 + 结构校验 + 转为 FaqItem 元组

加载规则：
    - 默认数据文件：find_project_root()/src/templates/assistant_templates/assistant_faq.yaml
    - 加载失败（文件缺失 / YAML 非法 / 结构不合法 / id 重复 / entry_path 不在
      入口目录）直接抛 ValueError 阻断启动——与配置加载同级别对待，避免带病运行
    - entry_path 校验依赖 ASSISTANT_ENTRY_CATALOG（入口目录是数据源权威）

演进预留：后续第 2 级（知识数据化 / 检索召回）只需替换本模块的数据来源
（如改为从数据库读取），上层 SystemPromptBuilder 不感知。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.constants.assistant import ASSISTANT_ENTRY_CATALOG
from src.utils.helpers import find_project_root


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
