#!/usr/bin/env python3
"""数据格式转换模块（精简）。

保留供 config / env 解析复用的通用字符串→基本类型转换函数；
其余（XML/JSON/YAML 互转、对象/字典互转）无引用，已于 2026-09-30 清理。
"""


# ============================================================
# 通用字符串 → 基本类型转换（供 config / env 解析等场景复用）
# ============================================================
def to_bool(value: str | None) -> bool:
    """将字符串转换为布尔值。
    仅当值（忽略大小写）为 ``"true"`` 时返回 ``True``，其余一律返回 ``False``。
    """
    return value.lower() == "true" if value else False


def to_int(value: str | None, default: int = 0) -> int:
    """将字符串转换为整数，无法转换时返回 *default*。"""
    return int(value) if value else default


def to_float(value: str | None, default: float = 0.0) -> float:
    """将字符串转换为浮点数，无法转换时返回 *default*。"""
    return float(value) if value else default
