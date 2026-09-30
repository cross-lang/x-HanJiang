#!/usr/bin/env python3
"""时间日期工具模块（精简）。

保留日期规范化函数（供 schemas 层用户/档案日期字段解析复用）；
其余（时间戳互转、周/月/季度边界、区间计算等）无引用，已于 2026-09-30 清理。
"""

from __future__ import annotations

import datetime


def normalize_date_str(value: object) -> str | None:
    """将任意日期输入规范化为本地日期字符串（YYYY-MM-DD）。

    兼容纯日期（2020-02-20）、ISO datetime（2020-02-19T16:00:00.000Z）、
    datetime/date 对象等。带时区的输入按 Asia/Shanghai 本地时区换算，
    避免时区偏移导致日期差一天。

    Args:
        value: 日期原始输入（str / datetime / date / None）

    Returns:
        str | None: 本地日期 YYYY-MM-DD；输入为 None 时返回 None

    Raises:
        ValueError: 无法识别的日期格式
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        dt = value
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
        return dt.strftime("%Y-%m-%d")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= 10 and not text.startswith(("T", " ")):
        return text[:10]
    try:
        dt = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"无法识别的日期格式: {text}") from exc
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d")
