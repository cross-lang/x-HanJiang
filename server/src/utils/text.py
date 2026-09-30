#!/usr/bin/env python3
"""文本处理模块（精简）。

保留 token 估算函数（供 AI 助手上下文预算使用）；
其余（KMP 检索、中文字符检测、哈希计算、CRC32、汉字转拼音等）无引用，
已于 2026-09-30 清理。
"""

from __future__ import annotations

#: 英文/数字/符号每个 token 的平均字符数（粗估系数）
_ASCII_CHARS_PER_TOKEN: int = 4
#: 中文/全角字符每个 token 的平均字符数（粗估系数）
_CJK_CHARS_PER_TOKEN: float = 1.5
#: 估算兜底常数，避免零输入返回 0 影响后续判断
_TOKEN_ESTIMATE_BASE: int = 1


def estimate_tokens(text: str) -> int:
    """估算一段文本的 token 数（启发式，无需依赖分词库）。

    说明：中文约 1.5 字符/token，英文/数字/符号约 4 字符/token；
    用于上下文预算的保守估算，非精确计费口径。

    Args:
        text: 待估算文本

    Returns:
        int: 估算的 token 数（至少为 1）
    """
    ascii_count = sum(1 for char in text if ord(char) < 0x80)
    cjk_count = len(text) - ascii_count
    estimated = int(ascii_count / _ASCII_CHARS_PER_TOKEN + cjk_count * _CJK_CHARS_PER_TOKEN)
    return max(estimated, _TOKEN_ESTIMATE_BASE)
