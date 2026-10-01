#!/usr/bin/env python3
"""大模型基础设施模块。

职责：封装大模型第三方客户端（openai SDK），业务层仅依赖抽象接口
LLMProvider，切换供应商只需新增实现类并修改配置，业务代码零改动。
本模块属于 infras/ 基础设施层，不依赖任何上层业务模块。

扩展约定：
    - 新增供应商：继承 LLMProvider 实现 chat_stream / chat / summarize，
      在 get_llm_provider 工厂中按配置 provider 分发即可
    - 文本向量化（embedding）与对话是两类独立模型能力，待 RAG / 长期记忆
      落地时在独立的 EmbeddingProvider 中提供，不混入本接口
    - 客户端初始化失败抛出 ExternalServiceException，不直接抛出第三方原生异常

同步形态说明：遵循工程规范「统一全同步形态」，使用 openai 同步客户端，
供 FastAPI 同步接口在线程池中调用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Final, cast

from openai import OpenAI, Stream
from openai._types import Omit
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionCustomToolParam,
    ChatCompletionFunctionToolParam,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
)

from src.core.config import settings
from src.core.exceptions import ExternalServiceException
from src.core.logger import logger

# 消息类型别名：统一使用 OpenAI 官方 ChatCompletionMessageParam 精确类型。
# 说明：底层 SDK 对 TypedDict 字面量校验较严，业务侧组装的 dict 在调用边界
# 通过 cast 显式转换（消息结构由本模块的对话协议保证）。
ChatMessage = list[ChatCompletionMessageParam]


@dataclass(frozen=True)
class ToolCall:
    """模型发起的工具调用。

    Attributes:
        id: 工具调用唯一标识（回填 tool 消息时使用 tool_call_id）
        name: 工具名称
        arguments: 工具入参（JSON 字符串）
    """

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class LLMChatResult:
    """一次非流式对话的返回结果。

    Attributes:
        raw_message: 模型返回的原始助手消息（含 role/content/tool_calls，
                     需原样回填到 messages 以继续多轮工具循环）
        content: 回复文本（可空，工具调用轮通常为空）
        tool_calls: 工具调用列表（可空）
    """

    raw_message: dict[str, object]
    content: str | None
    tool_calls: list[ToolCall] | None


class LLMProvider(ABC):
    """大模型提供者抽象接口。

    业务层只依赖此抽象，通过工厂（get_llm_provider）获取实例。
    """

    @abstractmethod
    def chat_stream(
        self,
        messages: ChatMessage,
        tools: list[dict[str, object]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """流式对话，逐 token 产出回复文本增量。

        Args:
            messages: 对话消息列表（含 system / user / assistant / tool）
            tools: 工具 schema 列表（可空）
            temperature: 采样温度（可空，使用配置默认值）
            max_tokens: 输出上限（可空，使用配置默认值）

        Yields:
            str: 回复文本增量

        Raises:
            ExternalServiceException: 大模型调用失败时抛出
        """

    @abstractmethod
    def chat(
        self,
        messages: ChatMessage,
        tools: list[dict[str, object]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMChatResult:
        """非流式对话，返回内容与工具调用。

        Args:
            messages: 对话消息列表
            tools: 工具 schema 列表（可空）
            temperature: 采样温度（可空）
            max_tokens: 输出上限（可空）

        Returns:
            LLMChatResult: 包含原始助手消息、文本内容与工具调用

        Raises:
            ExternalServiceException: 大模型调用失败时抛出
        """

    @abstractmethod
    def summarize(self, text: str) -> str:
        """将一段对话文本压缩为摘要（第 2 层滚动摘要使用）。

        Args:
            text: 待压缩的对话文本

        Returns:
            str: 压缩后的摘要

        Raises:
            ExternalServiceException: 大模型调用失败时抛出
        """


class OpenAICompatProvider(LLMProvider):
    """OpenAI 兼容协议实现。

    兼容 DeepSeek / 豆包（火山方舟）/ 通义 / 本地 vLLM 等所有
    提供 OpenAI 兼容 REST 接口的供应商，通过 base_url 切换。
    """

    _SUMMARY_SYSTEM_PROMPT: Final[str] = (
        "你是对话摘要助手。请把下面的对话内容压缩成一段中文摘要，"
        "保留关键事实、结论与用户需求，忽略寒暄与重复内容，不超过 200 字。"
    )

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
    ) -> None:
        """初始化 OpenAI 兼容客户端。

        Args:
            base_url: OpenAI 兼容服务地址
            api_key: API 密钥（敏感信息，来自配置，禁止打印）
            model: 对话模型名称
            timeout_seconds: 请求超时秒数

        Raises:
            ExternalServiceException: API Key 未配置时抛出
        """
        if not api_key:
            raise ExternalServiceException(message="AI 服务未配置（缺少 LLM_API_KEY），请在 .env 或环境变量中设置")
        self._client: OpenAI = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout_seconds,
        )
        self._model: str = model
        logger.info(f"OpenAICompatProvider initialized: model={model}, base_url={base_url}")

    def chat_stream(
        self,
        messages: ChatMessage,
        tools: list[dict[str, object]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        try:
            stream: Stream[ChatCompletionChunk] = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=self._to_sdk_tools(tools),
                stream=True,
                temperature=settings.ai.llm.temperature if temperature is None else temperature,
                max_tokens=settings.ai.llm.max_tokens if max_tokens is None else max_tokens,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:  # noqa: BLE001 - 统一转换为系统异常，避免暴露 SDK 原生异常
            raise ExternalServiceException(message=f"大模型流式调用失败: {exc}") from exc

    def chat(
        self,
        messages: ChatMessage,
        tools: list[dict[str, object]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMChatResult:
        try:
            completion: ChatCompletion = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=self._to_sdk_tools(tools),
                stream=False,
                temperature=settings.ai.llm.temperature if temperature is None else temperature,
                max_tokens=settings.ai.llm.max_tokens if max_tokens is None else max_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - 统一转换为系统异常，避免暴露 SDK 原生异常
            raise ExternalServiceException(message=f"大模型调用失败: {exc}") from exc
        message = completion.choices[0].message
        tool_calls: list[ToolCall] | None = None
        if message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
                    # 自定义工具调用（custom tool）暂不支持，跳过
                    continue
                tool_calls.append(
                    ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )
                )
        return LLMChatResult(
            raw_message=message.model_dump(exclude_none=True),
            content=message.content,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _to_sdk_tools(
        tools: list[dict[str, object]] | None,
    ) -> Iterable[ChatCompletionFunctionToolParam | ChatCompletionCustomToolParam] | Omit:
        """将通用工具声明字典转换为 SDK 类型（调用边界显式转换）。

        未提供工具时返回 Omit 哨兵，避免向 SDK 传 None。

        Args:
            tools: 通用工具声明列表（可空）

        Returns:
            Iterable[ChatCompletionFunctionToolParam | ChatCompletionCustomToolParam] | Omit:
                SDK 工具参数或省略哨兵
        """
        if not tools:
            return Omit()
        return cast(
            Iterable[ChatCompletionFunctionToolParam | ChatCompletionCustomToolParam],
            tools,
        )

    def summarize(self, text: str) -> str:
        messages: ChatMessage = [
            {"role": "system", "content": self._SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        result = self.chat(messages=messages, temperature=0.3, max_tokens=500)
        return result.content or ""


# ============================================================
# 工厂与单例
# ============================================================

_llm_provider: LLMProvider | None = None


def _create_llm_provider() -> LLMProvider:
    """根据配置创建大模型提供者实例。

    Returns:
        LLMProvider: 具体实现实例

    Raises:
        ExternalServiceException: 配置的供应商类型不支持时抛出
    """
    llm_cfg = settings.ai.llm
    if llm_cfg.provider == "openai_compat":
        return OpenAICompatProvider(
            base_url=llm_cfg.base_url,
            api_key=llm_cfg.api_key,
            model=llm_cfg.model,
            timeout_seconds=llm_cfg.timeout_seconds,
        )
    raise ExternalServiceException(message=f"不支持的模型供应商类型: {llm_cfg.provider}")


def get_llm_provider() -> LLMProvider:
    """获取缓存的 LLM 提供者（应用级别单例）。

    Returns:
        LLMProvider: LLM 提供者实例

    Raises:
        ExternalServiceException: 未配置或初始化失败时抛出
    """
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = _create_llm_provider()
    return _llm_provider


__all__ = [
    "ToolCall",
    "LLMChatResult",
    "LLMProvider",
    "OpenAICompatProvider",
    "get_llm_provider",
]
