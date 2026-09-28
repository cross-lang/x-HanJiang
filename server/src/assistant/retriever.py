#!/usr/bin/env python3
"""知识检索（RAG）预留：抽象接口 + 空实现。

当前 AI 助手为轻量版，不引入向量检索；本模块仅保留 RAG 能力位：
    - RetrieverProvider 抽象接口（retrieve）
    - NullRetriever 空实现（未启用时使用，返回空列表）
后续接入向量检索时实现 RetrieverProvider 子类，并在依赖工厂中按配置替换。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.config import settings
from src.core.exceptions import ExternalServiceException


@dataclass(frozen=True)
class RetrievedChunk:
    """检索返回的知识片段。

    Attributes:
        content: 片段内容
        score: 相关度得分（0~1，由具体检索实现给出）
    """

    content: str
    score: float


class RetrieverProvider(ABC):
    """知识检索提供者抽象接口（RAG 预留）。"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """根据查询返回相关知识片段。

        Args:
            query: 查询文本
            top_k: 返回片段数上限

        Returns:
            list[RetrievedChunk]: 知识片段列表（可空）
        """


class NullRetriever(RetrieverProvider):
    """空检索实现（RAG 未启用时使用）。"""

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        return []


# ============================================================
# 工厂
# ============================================================


def get_retriever_provider() -> RetrieverProvider:
    """按配置创建检索提供者实例。

    Returns:
        RetrieverProvider: 检索实现实例

    Raises:
        ExternalServiceException: 配置的检索类型不支持时抛出
    """
    provider = settings.ai.retriever.provider
    if provider == "null":
        return NullRetriever()
    raise ExternalServiceException(message=f"不支持的检索提供者类型: {provider}")
