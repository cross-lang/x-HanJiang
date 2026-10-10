#!/usr/bin/env python3
"""正文内联工具调用：文本形式工具调用的协议防御。

TL;DR —— 本模块做什么：
    部分推理模型偶发把工具调用以文本形式写进回复正文（<tool_call> XML 或
    JSON 对象/数组），流式透出后无法收回。本模块提供两件配合的武器：
        - InlineToolCallGate：流式检测门，在正文增量透出前扣留可疑前缀，
          对普通对话零延迟；
        - extract_text_tool_call：终判解析，把扣留的完整文本识别为 ToolCall
          （或判定为普通文本）。

如何使用（入口在 src/assistant/agent.py 的 agent 循环）：
    gate = InlineToolCallGate()
    for piece in gate.feed(delta_text):        # 返回当前可安全放行的片段
        yield token 事件(piece)
    ...流结束...
    if gate.is_holding:                        # 仍扣留 → 终判
        call = extract_text_tool_call(full_content)
        # 是工具调用 → 执行（内容从未泄漏）；否则 gate.release() 放行

识别的文本形式（详见 extract_text_tool_call）：
    - XML：<tool_call><tool_name>navigate</tool_name><path>/roles</path></tool_call>
    - JSON 对象：{"action": "navigate", ...} / {"tool_calls": [...]} / {"function": {...}}
    - JSON 数组：[{"action": ...}, ...]（部分模型输出候选动作数组）

依赖说明：仅依赖 ToolCall（infras/llm 协议对象）与入口目录常量，
零仓储依赖，可独立单测。
"""

from __future__ import annotations

import json
import re

from src.constants.assistant import ASSISTANT_ENTRY_CATALOG
from src.infras.llm import ToolCall


def page_of_path(path: str) -> str | None:
    """入口路由路径 → 页面码（供文本工具调用兜底映射）。

    NavigateTool 入参使用入口页面码（page），而模型文本形式的工具调用
    常写出路由路径（path），需要在此换算。

    Args:
        path: 入口路由路径（如 /roles）

    Returns:
        str | None: 对应的页面码；不在入口目录中返回 None
    """
    for item in ASSISTANT_ENTRY_CATALOG:
        if item["path"] == path:
            return item["page"]
    return None


class InlineToolCallGate:
    """流式正文内联工具调用检测门。

    背景：流式优先改造后，正文增量会实时发给前端；但推理模型偶发把工具
    调用写进正文（<tool_call> XML 或 JSON，详见 extract_text_tool_call），
    一旦透出无法收回。

    策略（对普通对话零延迟）：
        - 只扣留「首个非空白字符为 < / { / [」的回复进行观察；
        - 前缀一旦不可能匹配工具调用语法，立即补发扣留内容并转直放；
        - 流结束仍未排除嫌疑的，由调用方用 extract_text_tool_call 终判：
          是工具调用则执行（内容从未泄漏），否则调用 release() 放行。

    状态流转：watch（尚未见首字符）→ bypass（直放）/ hold（扣留观察）。
    """

    _XML_TAG: str = "<tool_call>"

    def __init__(self) -> None:
        """初始化：watch 状态、空缓冲。"""
        self._state: str = "watch"
        self._buffer: str = ""

    def feed(self, text: str) -> list[str]:
        """接收一段正文增量，返回当前可安全放行的文本。

        Args:
            text: 正文增量

        Returns:
            list[str]: 可立即下发的片段（直放时为整段，扣留时为空列表）
        """
        if self._state == "bypass":
            return [text]
        self._buffer += text
        if self._state == "watch":
            stripped = self._buffer.lstrip()
            if not stripped:
                return []
            first = stripped[0]
            if first not in ("<", "{", "["):
                self._state = "bypass"
                release, self._buffer = self._buffer, ""
                return [release]
            self._state = "hold"
        return self._classify()

    def _classify(self) -> list[str]:
        """hold 状态下判断缓冲前缀是否仍可能是工具调用。

        Returns:
            list[str]: 排除嫌疑时返回全部扣留内容（同时转直放）；否则空列表
        """
        stripped = self._buffer.strip()
        if stripped[0] == "<":
            # XML：去空白缓冲必须仍是 <tool_call> 的前缀，或已含完整开标签
            compatible = self._XML_TAG.startswith(stripped) or stripped.startswith(self._XML_TAG)
            if not compatible:
                return self._release_all()
            return []
        # JSON：能解析 → 完整 JSON，扣留到流终；
        # 报错位置在「增长边缘」→ 可能只是未写完，继续等；
        # 报错位置在缓冲内部 → 追加文本无法修复，排除嫌疑立即放行。
        try:
            json.loads(self._buffer)
        except json.JSONDecodeError as exc:
            edge = len(self._buffer.rstrip())
            if exc.pos < edge - 1:
                return self._release_all()
        return []

    def _release_all(self) -> list[str]:
        """转直放并返回全部扣留内容。

        Returns:
            list[str]: 含全部扣留文本的单元素列表
        """
        self._state = "bypass"
        release, self._buffer = self._buffer, ""
        return [release]

    @property
    def is_holding(self) -> bool:
        """流结束时是否仍处扣留态（待调用方终判）。"""
        return self._state == "hold"

    def release(self) -> str:
        """终判非工具调用后放行扣留内容（仅 is_holding 时调用）。

        Returns:
            str: 全部扣留文本
        """
        held, self._buffer = self._buffer, ""
        self._state = "bypass"
        return held


def extract_text_tool_call(content: str | None) -> ToolCall | None:
    """从回复正文中识别模型以文本形式输出的工具调用（兜底）。

    部分推理模型（如 mimo-v2.6-pro）偶发把函数调用写进正文而非结构化
    tool_calls，常见形式：
        - XML：<tool_call><tool_name>navigate</tool_name><path>/roles</path></tool_call>
        - JSON 对象：{"action": "navigate", "path": "/roles"}
        或 OpenAI 文本形式：{"tool_calls": [{"function": {"name": ..., "arguments": ...}}]}
        - JSON 数组：[{"action": "navigate", "action_input": {"path": "/users"}}]
            （部分模型以数组形式输出候选动作，元素可为 navigate 动作或 function 调用）
    识别后转为 ToolCall，交由 agent 循环正常执行，避免把内部结构
    作为回复正文展示给用户。

    Args:
        content: 模型回复正文（可空）

    Returns:
        ToolCall | None: 识别出的工具调用；非工具调用文本返回 None
    """
    if not content or not content.strip():
        return None
    text = content.strip()
    # 形式 A：XML 标签
    xml_match = re.search(
        r"<tool_call>\s*<tool_name>(\w+)</tool_name>(.*?)</tool_call>",
        text,
        re.DOTALL,
    )
    if xml_match is not None:
        name: str = xml_match.group(1)
        args_xml: str = xml_match.group(2)
        args: dict[str, str] = {}
        for tag, value in re.findall(r"<(\w+)>([^<]+)</\1>", args_xml):
            args[tag] = value.strip()
        return ToolCall(id="text-call", name=name, arguments=json.dumps(args, ensure_ascii=False))
    # 形式 B：JSON 对象或数组（navigate 动作 / tool_calls / function 调用）
    try:
        payload: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    candidates: list[object] = payload if isinstance(payload, list) else [payload]
    for item in candidates:
        if not isinstance(item, dict):
            continue
        call = _parse_text_call_item(item)
        if call is not None:
            return call
    return None


def _parse_text_call_item(item: dict[str, object]) -> ToolCall | None:
    """从单个 JSON 对象识别文本工具调用。

    支持三类：
        1. navigate 动作：{"action": "navigate", "page"/"path"/"action_input"}
        2. tool_calls 数组：{"tool_calls": [{"function": {"name", "arguments"}}]}
        3. function 调用：{"function": {"name": ..., "arguments": ...}}（数组元素常见序列化）
    """
    action = item.get("action")
    if isinstance(action, str) and action == "navigate":
        return _build_navigate_call(item)
    calls = item.get("tool_calls")
    if isinstance(calls, list) and calls:
        first: object = calls[0]
        if isinstance(first, dict):
            fn = first.get("function")
            if isinstance(fn, dict):
                fn_name: object = fn.get("name")
                fn_args: object = fn.get("arguments")
                if isinstance(fn_name, str) and isinstance(fn_args, str):
                    return ToolCall(
                        id=str(first.get("id") or "text-call"),
                        name=fn_name,
                        arguments=fn_args,
                    )
    fn = item.get("function")
    if isinstance(fn, dict):
        fn_name = fn.get("name")
        fn_args = fn.get("arguments")
        if isinstance(fn_name, str) and isinstance(fn_args, str):
            return ToolCall(
                id=str(item.get("id") or "text-call"),
                name=fn_name,
                arguments=fn_args,
            )
    return None


def _build_navigate_call(item: dict[str, object]) -> ToolCall | None:
    """从 navigate 动作对象构造 ToolCall。

    支持 page / path / action_input 三种字段定位目标页；
    action_input 既可为字符串（页面标识或路由）也可为嵌套 dict（含 page/path）。

    Returns:
        ToolCall | None: 参数有效时返回 navigate 调用；参数缺失返回 None
    """
    page = item.get("page")
    if isinstance(page, str) and page:
        return ToolCall(
            id="text-call",
            name="navigate",
            arguments=json.dumps({"page": page}, ensure_ascii=False),
        )
    path = item.get("path")
    if isinstance(path, str) and path:
        mapped = page_of_path(path)
        return ToolCall(
            id="text-call",
            name="navigate",
            arguments=json.dumps({"page": mapped if mapped is not None else ""}, ensure_ascii=False),
        )
    action_input = item.get("action_input")
    if isinstance(action_input, dict):
        sub_page = action_input.get("page")
        if isinstance(sub_page, str) and sub_page:
            return ToolCall(
                id="text-call",
                name="navigate",
                arguments=json.dumps({"page": sub_page}, ensure_ascii=False),
            )
        sub_path = action_input.get("path")
        if isinstance(sub_path, str) and sub_path:
            mapped = page_of_path(sub_path)
            return ToolCall(
                id="text-call",
                name="navigate",
                arguments=json.dumps({"page": mapped if mapped is not None else ""}, ensure_ascii=False),
            )
    if isinstance(action_input, str) and action_input:
        mapped = page_of_path(action_input)
        return ToolCall(
            id="text-call",
            name="navigate",
            arguments=json.dumps(
                {"page": mapped if mapped is not None else action_input},
                ensure_ascii=False,
            ),
        )
    return None
