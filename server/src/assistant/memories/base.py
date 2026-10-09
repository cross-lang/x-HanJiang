#!/usr/bin/env python3
"""记忆层统一抽象与层间编排上下文。

本模块定义各记忆层的公共契约：
    - MemoryContext：层间传递的「消息 + 剩余预算 + 本轮动态内容」黑板
    - MemoryLayer：层统一抽象（Strategy），每层只负责向 ctx 贡献本层记忆
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from src.models.entities.assistant_entity import AssistantConversationEntity


@dataclass
class MemoryContext:
    """层间编排状态：在各 MemoryLayer 之间传递（黑板 / Blackboard 模式）。

    Attributes:
        messages: 已累积的上下文消息（按层注入顺序）
        remaining_budget: 剩余 token 预算（各层占用后递减；供 L3 裁剪）
        user_permissions: 当前用户权限码集合（L0 据此过滤系统入口路由表；
            空集表示未传入，L0 不过滤；含 "*" 表示超级管理员通配）
        user_context: L1 用户档案文本（由 MemoryFacade 取好后注入 ctx，
            L0 读取渲染进系统提示词；空串表示无档案）
        retriever_context: RAG 检索补充知识（由 MemoryFacade 取好后注入 ctx，
            L0 读取渲染进系统提示词；空串表示无补充知识）

    设计说明：
        让各层共享同一个可变上下文，而不是每层各自返回一个列表再由
        MemoryFacade 拼接，好处是——① 消息追加与预算扣减集中记账，不会出现
        某层忘记扣预算；② 层与层之间互不持有引用、互不感知，只读写 ctx，
        新增/调整层顺序时其他层零改动。
        L1 用户档案与 RAG 补充知识也走 ctx：MemoryFacade 在驱动各层之前，
        先把这两个「本轮动态内容」取好写入 ctx.user_context /
        ctx.retriever_context，L0 直接读取，从而 L0 不再持有 L1 /
        RAG 的引用——L0 退化为纯渲染适配器，与记忆层 / 检索层彻底解耦。

    不变式：
        - remaining_budget 永远 ≥ 0（charge 用 max(...,0) 兜底）；
        - messages 的下标顺序严格等于层的注入顺序（L0 在前、L3 在后）；
        - user_context / retriever_context 在层循环开始前由 Facade 一次性写定，
          各层只读不写；
        - 「追加内容」与「扣减预算」是两个正交动作：append 只加消息、
          charge 只减预算，由各层按需分别调用，不强行绑定。
    """

    messages: list[dict[str, object]] = field(default_factory=list)
    remaining_budget: int = 0
    user_permissions: set[str] = field(default_factory=set)
    user_context: str = ""
    retriever_context: str = ""

    def append(self, role: str, content: str) -> None:
        """追加一条消息。

        Args:
            role: 消息角色（system / user / assistant）
            content: 消息内容
        """
        self.messages.append({"role": role, "content": content})

    def charge(self, tokens: int) -> None:
        """从剩余预算中扣除已占用 token（不产生负预算）。

        Args:
            tokens: 本层占用的 token 数
        """
        self.remaining_budget = max(self.remaining_budget - tokens, 0)


class MemoryLayer(ABC):
    """记忆层统一抽象（Strategy）：每层只负责向编排上下文贡献本层记忆。

    类属性:
        order: 层编号（同时表明注入优先级，数字越小优先级越高）

    接口契约（实现 contribute 时必须遵守）：
        - 命令式：通过修改传入的 ctx 产生结果（append / charge），返回 None；
          不用返回值表达消息，因为单层可能注入 0 条（无摘要）到多条（L3
          按预算动态决定条数），返回单条或列表都无法统一；
        - 只读边界：contribute 不得写库、不得 commit。写库是「沉淀」语义，
          只发生在 L2 的 consolidate（该方法不在本统一接口内）；
        - 层间隔离：不得感知或调用其他层，跨层信息一律走 ctx；
        - 依赖来源：只可使用构造时注入的端口 / 适配器，不新建全局资源。

    order 字段说明：
        当前注入顺序由 MemoryFacade 中 layers 的元组顺序显式决定（更直观、
        可插入重排）；order 主要作为层的身份标识与可读性提示，也为将来
        需要「按编号动态收集/排序各层」预留元数据。
    """

    order: ClassVar[int]

    @abstractmethod
    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """将本层记忆注入编排上下文（追加消息 + 扣减预算）。

        Args:
            ctx: 层间编排上下文
            conversation: 会话实体
            user_id: 当前用户ID
            query: 本轮用户输入
        """
