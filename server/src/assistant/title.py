#!/usr/bin/env python3
"""AI 助手会话主题命名：根据对话内容自动归纳会话主题名。

职责：
    - generate_title()：基于「滚动摘要 + 本轮问答」调用大模型生成简短主题名
    - 供 assistant_service 每轮对话完成后调用，写入 conversation.title

设计说明：
    - 命名输入融合第 2 层滚动摘要（远历史要点）与本轮问答（最新主题），
      避免仅凭首轮或仅凭本轮导致的名字偏差
    - 输出约束：≤ 12 个汉字、无标点、无引号；异常上抛由调用方静默处理，
      绝不因命名失败影响主对话流程
    - 演进预留：后续支持用户手动改名时，本模块仅作为「自动命名」策略之一
"""

from __future__ import annotations

from typing import cast

from src.core.exceptions import ExternalServiceException
from src.infras.llm import ChatMessage, LLMProvider

# 主题名长度上限（防止模型异常输出超长文本）
_TITLE_MAX_LENGTH: int = 30

_TITLE_SYSTEM_PROMPT: str = (
    "你是会话主题命名助手。根据下面这段对话内容，用不超过 12 个汉字概括这段对话的主题，"
    "直接输出主题名即可：不要标点、不要引号、不要解释、不要寒暄。"
)


def generate_title(
    llm: LLMProvider,
    *,
    summary: str,
    query: str,
    reply: str,
) -> str:
    """归纳对话主题名。

    Args:
        llm: 大模型提供方
        summary: 会话滚动摘要（远历史要点，可为空串）
        query: 本轮用户输入
        reply: 本轮助手最终回复（兜底跳转文案或正常回答）

    Returns:
        str: 清洗后的主题名（≤ 30 字符）

    Raises:
        ExternalServiceException: 大模型调用失败时抛出
    """
    dialog_text = (
        f"历史摘要：{summary if summary else '（无）'}\n"
        f"用户：{query}\n"
        f"助手：{reply}"
    )
    result = llm.chat(
        messages=cast(
            ChatMessage,
            [
                {"role": "system", "content": _TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": dialog_text},
            ],
        ),
        temperature=0.2,
        # 推理模型（如 MiMo）的思考过程占用输出 token 预算，
        # 预算过小会导致思考未完成即截断、content 为空；1024 可保证最终答案输出
        max_tokens=1024,
    )
    title = (result.content or "").strip().strip('"“”\'').strip()
    return title[:_TITLE_MAX_LENGTH]
