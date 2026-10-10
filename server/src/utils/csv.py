#!/usr/bin/env python3
"""CSV 导出 / 解析工具。

统一封装「dict 行列表 → UTF-8-BOM CSV 下载响应」与「CSV 文本 → dict 行列表」两类操作，
消除各业务模块（审计日志、用户管理等）中重复的 CSV 处理代码。

约定：
- 导出统一使用 UTF-8-BOM 编码（Excel 可直接打开，中文不乱码）；
- 首行输出中文表头（headers_cn），列顺序由 fieldnames 决定；
- 行内缺失字段补空串，不在 fieldnames 中的字段被忽略。
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi.responses import StreamingResponse


def build_csv_stream_response(
    *,
    fieldnames: list[str],
    headers_cn: dict[str, str],
    rows: Iterable[dict[str, Any]],
    filename: str,
) -> StreamingResponse:
    """将 dict 行序列化为 CSV 文件下载响应。

    Args:
        fieldnames: 列顺序与取值键（CSV 列名，一般使用英文字段名）
        headers_cn: 字段名 → 中文表头映射，作为首行输出
        rows: 数据行（每行为 dict，缺失字段自动补空串）
        filename: Content-Disposition 下载文件名，如 ``用户_20261006123000.csv``；
            支持中文名（自动按 RFC 5987 编码，兼容现代浏览器）

    Returns:
        StreamingResponse: CSV 下载响应（text/csv，UTF-8-BOM 编码）
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writerow(headers_cn)
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    content = buf.getvalue().encode("utf-8-sig")
    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"download{Path(filename).suffix}\"; filename*=UTF-8''{encoded_filename}"
            )
        },
    )


def parse_csv_rows(content: str) -> list[dict[str, str]]:
    """解析 CSV 文本为 dict 行列表。

    首行作为表头，返回每行的 ``{列名: 值}`` 字典。
    调用方应传入已解码的文本（如 ``content.decode("utf-8-sig")``），
    本函数不处理编码解码，保持与导出侧（UTF-8-BOM）约定对称。

    Args:
        content: CSV 文本内容

    Returns:
        list[dict[str, str]]: 按表头解析出的行列表
    """
    return list(csv.DictReader(content.splitlines()))
