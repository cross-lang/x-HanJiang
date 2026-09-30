#!/usr/bin/env python3
"""SSE（Server-Sent Events）协议工具。

提供 SSE 数据帧的格式化函数，供流式响应端点复用。
"""

from __future__ import annotations

import json
from typing import Any


def build_sse_event(data: dict[str, Any]) -> str:
    """将事件字典序列化为 SSE 数据帧。

    输出格式：``data: <json>\\n\\n``（每帧以空行结尾，符合 SSE 协议）。

    Args:
        data: 事件字典

    Returns:
        str: 完整 SSE 帧（data: <json>\\n\\n）
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
