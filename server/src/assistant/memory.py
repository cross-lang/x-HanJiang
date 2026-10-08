#!/usr/bin/env python3
"""记忆系统：四层记忆的类封装与统一编排。

分层结构（每层一个内聚类，MemoryManager 只做编排，不写具体记忆逻辑）：
    第 0 层 · 系统提示词   永不丢弃，固定预算
                     SystemPromptLayer —— 适配 knowledge.SystemPromptBuilder
                     （身份设定 / 系统入口清单 / FAQ），并并入 RAG 补充知识
    第 1 层 · 长期记忆     跨会话用户档案 ——【当前仅预留接口】
                     UserMemoryProvider 抽象 + NullUserMemory 空实现。
                     语义上档案填进 L0 提示词的 {user_block} 槽位，由 L0
                     消费，故 L1 是「内容提供者」而非「消息层」，不实现
                     MemoryLayer 接口（不为对称而破坏语义）
    第 2 层 · 滚动摘要     窗口外旧消息渐进压缩（Conversation.summary）
                     SummaryMemoryLayer —— contribute 注入摘要消息；
                     consolidate 执行压缩（对话结束后由 Manager 调用）
    第 3 层 · 最近 N 轮原文 精确保留最近几轮（超预算从最旧一条丢弃）
                     RecentMemoryLayer —— 在剩余预算内反向贪心选取

编排机制：
    MemoryLayer 统一抽象 contribute(ctx, ...)；MemoryContext 在层间传递
    「已累积消息 + 剩余 token 预算」。MemoryManager 持有按 L0 → L2 → L3
    排序的层列表并遍历，对外暴露 build_context / roll_summary。

依赖倒置（避免上层耦合与循环导入）：
    各层不直接依赖具体仓储，只面向本模块存储端口（MessageRepository /
    ConversationRepository，Protocol），仓储结构化满足，由装配层注入。
    SystemPromptBuilder / ORM 实体仅在 TYPE_CHECKING 下导入，运行时零循环导入。

一轮对话的数据流（build_context 内部）：

    ┌─────────────┐  contribute   ┌──────────────┐
    │ L0 提示词层 │ ───────────▶  │              │ 注入 system 提示词
    └─────────────┘               │              │ 并 charge 其 token
    ┌─────────────┐  contribute   │ MemoryContext│
    │ L2 摘要层   │ ───────────▶  │  .messages   │ 注入「历史摘要」
    └─────────────┘               │  .remaining_ │ （无摘要则跳过）
    ┌─────────────┐  contribute   │   budget     │
    │ L3 原文层   │ ───────────▶  │              │ 在剩余预算内从新
    └─────────────┘               └──────────────┘ 到旧贪心选原文
           │
           ▼ 对话结束、回复落库后
    Manager.roll_summary → L2.consolidate：把窗口外最旧消息 LLM 压缩进
    Conversation.summary 并删除原文（L2 的「写入/沉淀」反向操作）

预算流转示例（token_budget=32000）：
    初始 remaining_budget = 32000
    L0 注入提示词（假设 2000 tok）→ charge → 剩余 30000
    L2 注入摘要（假设 800 tok）    → charge → 剩余 29200
    L3 在 ≤29200 额度内从最新一条反向累加；装不下的更旧原文被丢弃
    口径说明：token_budget 只覆盖「系统提示词 + 历史上下文」，不含本轮
    用户消息与模型输出预留。

阅读导引：
    想了解「某层干什么」→ 看对应 *Layer 类的类 docstring；
    想了解「层如何被驱动」→ 看 MemoryLayer 抽象与 MemoryManager；
    想了解「层之间传什么」→ 看 MemoryContext；
    想了解「数据从哪来」→ 看 MessageRepository / ConversationRepository 端口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Protocol

from src.assistant.retriever import RetrieverProvider, get_retriever_provider
from src.constants.assistant import (
    ASSISTANT_ROLL_CHUNK_SIZE,
    ASSISTANT_ROLL_TRIGGER_FACTOR,
)
from src.core.config import settings
from src.core.logger import logger
from src.infras.llm import LLMProvider, get_llm_provider
from src.utils.text import estimate_tokens

if TYPE_CHECKING:
    from src.assistant.knowledge import SystemPromptBuilder
    from src.models.entities.assistant_entity import AssistantConversationEntity


# ============================================================
# 第 1 层：长期记忆抽象（当前仅预留接口；内容供 L0 消费）
# ============================================================


class UserMemoryProvider(ABC):
    """用户长期记忆提供者（第 1 层抽象接口）。

    后续接入方式：
        1. 新增 user_profile 表（用户长期偏好 / 关注点）
        2. 实现子类读取该表并返回档案文本
        3. 替换装配层中的 NullUserMemory 为真实实现
    """

    @abstractmethod
    def load_user_context(self, user_id: int) -> str:
        """返回注入系统提示词的『用户档案』文本。

        Args:
            user_id: 用户ID

        Returns:
            str: 档案文本；未接入长期记忆时返回空串
        """


class NullUserMemory(UserMemoryProvider):
    """长期记忆空实现（占位）。

    第 1 层未启用时使用，返回空串，保证上层提示词组装逻辑不变。
    """

    def load_user_context(self, user_id: int) -> str:
        return ""


# ============================================================
# 存储端口（Ports）：记忆层所需持久化能力，仓储结构化满足
# ============================================================
#
# 为什么用 typing.Protocol 而不是让仓储继承 ABC：
#   1. 结构化子类型（structural subtyping）：仓储无需显式声明继承、
#      也无需为接入记忆系统做任何改动，只要方法签名匹配即被 mypy /
#      pyright 认可——对仓储零侵入；
#   2. 端口由「消费方」（记忆子系统）定义，是依赖倒置：记忆层不认识
#      SQLAlchemy，也不关心数据来自 MySQL 还是其他实现，可被内存 fake
#      轻松替换，便于单测；
#   3. 接口隔离：拆成 MessageRepository（消息读写）与 ConversationRepository
#      （摘要持久化 + commit），L3 只依赖消息读取，不被迫看到摘要接口。
#
# 事务边界约定：端口方法（delete_by_ids 等）内部只做 flush，不 commit；
# 真正提交统一走 ConversationRepository.commit，保证「提交权在记忆/服务边界」。


class MessageRecord(Protocol):
    """消息记录最小结构（AssistantMessageEntity 结构化满足）。"""

    id: int
    role: str
    content: str


class MessageRepository(Protocol):
    """消息存储端口：第 3 层原文读取 + 第 2 层压缩时移除旧消息。"""

    def list_by_conversation(
        self, conversation_id: int, limit: int = 100
    ) -> list[MessageRecord]:
        """按时间正序返回会话最近 limit 条消息。"""

    def count_by_conversation(self, conversation_id: int) -> int:
        """统计会话消息总数。"""

    def list_oldest_outside_window(
        self,
        conversation_id: int,
        keep_count: int,
        limit: int = 10,
    ) -> list[MessageRecord]:
        """跳过最近 keep_count 条，按时间正序返回最旧的 limit 条。"""

    def delete_by_ids(self, message_ids: list[int]) -> None:
        """按主键批量删除已折入摘要的旧消息。"""


class ConversationRepository(Protocol):
    """会话存储端口：第 2 层摘要持久化。"""

    def update_summary(self, conversation_id: int, summary: str) -> None:
        """更新会话滚动摘要。"""

    def commit(self) -> None:
        """提交事务（提交权归属服务/记忆边界，仓储只 flush）。"""


# ============================================================
# 记忆层统一抽象 + 层间编排上下文
# ============================================================


@dataclass
class MemoryContext:
    """层间编排状态：在各 MemoryLayer 之间传递（黑板 / Blackboard 模式）。

    Attributes:
        messages: 已累积的上下文消息（按层注入顺序）
        remaining_budget: 剩余 token 预算（强制层占用后递减；供 L3 裁剪）

    设计说明：
        让各层共享同一个可变上下文，而不是每层各自返回一个列表再由
        Manager 拼接，好处是——① 消息追加与预算扣减集中记账，不会出现
        某层忘记扣预算；② 层与层之间互不持有引用、互不感知，只读写 ctx，
        新增/调整层顺序时其他层零改动。

    不变式：
        - remaining_budget 永远 ≥ 0（charge 用 max(...,0) 兜底）；
        - messages 的下标顺序严格等于层的注入顺序（L0 在前、L3 在后）；
        - 「追加内容」与「扣减预算」是两个正交动作：append 只加消息、
          charge 只减预算，由各层按需分别调用，不强行绑定。
    """

    messages: list[dict[str, object]] = field(default_factory=list)
    remaining_budget: int = 0

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
        当前注入顺序由 Manager 中 _layers 的列表顺序显式决定（更直观、
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


# ============================================================
# 第 0 层：系统提示词（适配 SystemPromptBuilder + 并入 RAG）
# ============================================================


class SystemPromptLayer(MemoryLayer):
    """第 0 层：系统提示词（最高优先级，永不丢弃）。

    作为 MemoryLayer 与 SystemPromptBuilder 之间的适配器：L0 的具体内容仍由
    SystemPromptBuilder 组装，本类负责 RAG 检索、调用并把结果纳入预算记账。

    职责：
        1. 按开关做 RAG 检索，得到补充知识（未启用时空串）；
        2. 委托 SystemPromptBuilder 组装完整系统提示词（其中已含 L1 用户档案、
           入口清单与 FAQ）；
        3. 向 ctx 追加该 system 消息并按实际 token 扣减预算。

    不变式：
        - 每轮恰好注入 1 条 role="system" 的消息；
        - 作为第一个执行的层（order=0），其 charge 决定 L2/L3 的可用预算；
        - 不读取 conversation、不写库（纯只读 + ctx 写入）；
        - 即便 remaining_budget=0 也照常注入：L0 优先级最高，预算缺口由
          后面的 L3「少带原文」来吸收，而不是压缩提示词本身。
    """

    order: ClassVar[int] = 0

    def __init__(
        self,
        system_prompt_builder: SystemPromptBuilder,
        retriever: RetrieverProvider,
    ) -> None:
        """初始化第 0 层。

        Args:
            system_prompt_builder: 系统提示词组装器（L1 用户档案经其内部注入）
            retriever: RAG 检索提供者
        """
        self._system_prompt_builder: SystemPromptBuilder = system_prompt_builder
        self._retriever: RetrieverProvider = retriever

    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """组装并注入系统提示词（RAG 补充知识在此并入）。

        Args:
            ctx: 层间编排上下文
            conversation: 会话实体（本层不使用，保持接口一致）
            user_id: 当前用户ID
            query: 本轮用户输入（FAQ 命中与 RAG 检索用）
        """
        retriever_context = self._retrieve_context(query)
        system_prompt = self._system_prompt_builder.build_system_prompt(
            user_id, retriever_context=retriever_context, user_question=query
        )
        ctx.append("system", system_prompt)
        ctx.charge(estimate_tokens(system_prompt))

    def _retrieve_context(self, query: str) -> str:
        """获取检索补充知识（RAG；未启用时返回空串）。

        Args:
            query: 查询文本

        Returns:
            str: 补充知识文本（空串表示无）
        """
        if not settings.ai.retriever.enabled:
            return ""
        chunks = self._retriever.retrieve(query, top_k=settings.ai.retriever.top_k)
        return "\n".join(chunk.content for chunk in chunks)


# ============================================================
# 第 2 层：滚动摘要（读取注入 + 压缩沉淀）
# ============================================================


class SummaryMemoryLayer(MemoryLayer):
    """第 2 层：滚动摘要（窗口外历史的压缩记忆，整体保留）。

    本层是唯一同时拥有「读路径」与「写路径」的层：
        - 读路径 contribute（实现统一接口）：把已有摘要作为一条 system
          消息注入上下文，属于组装阶段，只读不写；
        - 写路径 consolidate（本层特有，不在 MemoryLayer 接口内）：对话
          结束后由 Manager 调用，把窗口外最旧消息经 LLM 压缩进 summary、
          删除原文并提交，是记忆从 L3「沉淀」到 L2 的反向操作。

    职责：
        contribute —— 有摘要注入「历史摘要：…」，无摘要则完全跳过；
        consolidate —— 统计总数 → 取窗口外最旧的一块 → 与旧摘要拼接后
                       summarize → 更新摘要、删除原文、commit。

    不变式：
        - 摘要整体保留：要么注入完整摘要、要么不注入，不对摘要做局部裁剪
          （压缩发生在 consolidate，而不是组装时）；
        - 分批折入：每次只处理 ASSISTANT_ROLL_CHUNK_SIZE 条，避免单次
          prompt 过长 / LLM 负担过重，靠多轮对话渐进压缩；
        - consolidate 成功后，内存对象 conversation.summary 与库中字段
          保持一致，且被删原文与新增摘要在同一事务内提交。

    层间关系：在 L0 之后、L3 之前执行，其 charge 会进一步缩小 L3 额度。
    """

    order: ClassVar[int] = 2

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        llm_provider_getter: Callable[[], LLMProvider],
    ) -> None:
        """初始化第 2 层。

        Args:
            conversation_repository: 会话存储端口（摘要持久化 + 提交）
            message_repository: 消息存储端口（压缩时取/删旧消息）
            llm_provider_getter: LLM 获取器（summarize 调用，懒加载）
        """
        self._conversation_repository: ConversationRepository = conversation_repository
        self._message_repository: MessageRepository = message_repository
        self._get_llm: Callable[[], LLMProvider] = llm_provider_getter

    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """注入历史摘要消息（无摘要时跳过）。

        Args:
            ctx: 层间编排上下文
            conversation: 会话实体（摘要来源）
            user_id: 当前用户ID（本层不使用，保持接口一致）
            query: 本轮用户输入（本层不使用，保持接口一致）
        """
        if not conversation.summary:
            return
        content = f"历史摘要：{conversation.summary}"
        ctx.append("system", content)
        ctx.charge(estimate_tokens(content))

    def consolidate(self, conversation: AssistantConversationEntity) -> None:
        """滚动摘要压缩：窗口外旧消息渐进折入 summary 并删除原文。

        触发条件：记忆开关开启且消息总数超过（recent_raw_rounds × 2）；
        每次折入 ASSISTANT_ROLL_CHUNK_SIZE 条最旧消息，避免单次压缩过重。

        Args:
            conversation: 会话实体
        """
        memory_cfg = settings.ai.memory
        if not memory_cfg.enabled:
            return
        total = self._message_repository.count_by_conversation(conversation.id)
        keep_count = memory_cfg.recent_raw_rounds * ASSISTANT_ROLL_TRIGGER_FACTOR
        if total <= keep_count:
            return
        evicted = self._message_repository.list_oldest_outside_window(
            conversation.id,
            keep_count=keep_count,
            limit=ASSISTANT_ROLL_CHUNK_SIZE,
        )
        if not evicted:
            return
        chunk_text = "\n".join(f"{entity.role}: {entity.content}" for entity in evicted)
        previous = conversation.summary or ""
        combined = f"{previous}\n{chunk_text}" if previous else chunk_text
        new_summary = self._get_llm().summarize(combined)
        self._conversation_repository.update_summary(conversation.id, new_summary)
        conversation.summary = new_summary
        self._message_repository.delete_by_ids([entity.id for entity in evicted])
        self._conversation_repository.commit()
        logger.info(f"AI 助手滚动摘要：conversation={conversation.id} 折入 {len(evicted)} 条旧消息")


# ============================================================
# 第 3 层：最近 N 轮原文（剩余预算内反向贪心）
# ============================================================


class RecentMemoryLayer(MemoryLayer):
    """第 3 层：最近原文（最低优先级，超预算从最旧一条开始丢弃）。

    职责：
        取出最近窗口（recent_raw_rounds × 因子条）内的原文，在
        ctx.remaining_budget 额度内从「最新一条 → 更旧」反向贪心选取，
        再 reverse 回时间正序后并入上下文。

    选取策略的两个关键决策：
        - 遇到第一条装不下的消息立即 break，而不是跳过它去试更旧、更短的：
          近因连贯性比「硬凑条数」更重要，不能用一条更旧的短消息替换掉
          紧邻本轮的新消息，否则对话语境断裂；
        - 选完不调用 charge：本层是最后一个消费者，预算只用于决定「保留
          多少」，之后没有其他层需要读剩余预算，扣减没有意义。

    不变式：
        - 注入的消息严格保持原时间正序（最新的在最后、紧邻本轮用户消息）；
        - 可能注入 0 条（预算被 L0/L2 占满，或连最新一条都放不下）；
        - 纯只读 + ctx.messages 写入，不写库、不修改 remaining_budget。
    """

    order: ClassVar[int] = 3

    def __init__(self, message_repository: MessageRepository) -> None:
        """初始化第 3 层。

        Args:
            message_repository: 消息存储端口
        """
        self._message_repository: MessageRepository = message_repository

    def contribute(
        self,
        ctx: MemoryContext,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> None:
        """在剩余预算内注入最近原文（时间越近越优先保留）。

        存储端口按时间正序返回「最近 limit 条」，故从最新一条反向贪心累加：
        每条消息仅估算一次（O(n)），优先保住紧邻本轮的对话上下文。

        Args:
            ctx: 层间编排上下文（remaining_budget 即 L3 可用额度）
            conversation: 会话实体
            user_id: 当前用户ID（本层不使用，保持接口一致）
            query: 本轮用户输入（本层不使用，保持接口一致）
        """
        memory_cfg = settings.ai.memory
        keep_count = memory_cfg.recent_raw_rounds * ASSISTANT_ROLL_TRIGGER_FACTOR
        recent = self._message_repository.list_by_conversation(conversation.id, limit=keep_count)
        recent_messages: list[dict[str, object]] = []
        used_tokens = 0
        for entity in reversed(recent):
            msg_tokens = estimate_tokens(entity.content)
            if used_tokens + msg_tokens > ctx.remaining_budget:
                break
            used_tokens += msg_tokens
            recent_messages.append({"role": entity.role, "content": entity.content})
        recent_messages.reverse()
        ctx.messages.extend(recent_messages)


# ============================================================
# 记忆门面：编排各层（自身不写记忆逻辑）
# ============================================================


class MemoryManager:
    """记忆系统编排器（Facade）：持有有序记忆层并统一驱动。

    只负责编排，不包含具体记忆逻辑：
        - build_context：按 L0 → L2 → L3 顺序遍历各层 contribute
        - roll_summary：委托第 2 层 consolidate 执行压缩

    Attributes:
        _layers: 按注入优先级排序的记忆层列表（L0 / L2 / L3）
        _summary_layer: 第 2 层引用（压缩入口）

    生命周期与不变式：
        - 「层实例」长生命周期、可跨多轮复用：层的依赖（端口 / 适配器）
          在构造时固定，层自身不在 contribute 中累积跨轮状态；
        - 「MemoryContext」每轮一次性：build_context 每次新建 ctx，组装完
          即丢弃，杜绝上一轮消息/预算泄漏到下一轮；
        - _layers 在装配后不再变更（顺序即优先级），Manager 不做动态排序；
        - roll_summary 只做转发，不在此处判断是否该压缩——触发条件、取数、
          提交全部内聚在 L2.consolidate，保持 Manager 轻薄。
    """

    def __init__(
        self,
        system_prompt_builder: SystemPromptBuilder,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        retriever: RetrieverProvider | None = None,
        llm_provider_getter: Callable[[], LLMProvider] | None = None,
    ) -> None:
        """初始化记忆编排器并装配各记忆层。

        Args:
            system_prompt_builder: L0 系统提示词组装器
            conversation_repository: 会话存储端口
            message_repository: 消息存储端口
            retriever: RAG 检索提供者（缺省按配置工厂创建）
            llm_provider_getter: LLM 获取器（缺省使用全局懒加载工厂）
        """
        get_llm: Callable[[], LLMProvider] = llm_provider_getter or get_llm_provider
        self._summary_layer: SummaryMemoryLayer = SummaryMemoryLayer(
            conversation_repository=conversation_repository,
            message_repository=message_repository,
            llm_provider_getter=get_llm,
        )
        # 列表顺序即注入优先级（order 字段为层身份标识，供排查/扩展用）
        self._layers: list[MemoryLayer] = [
            SystemPromptLayer(system_prompt_builder, retriever or get_retriever_provider()),
            self._summary_layer,
            RecentMemoryLayer(message_repository),
        ]

    def build_context(
        self,
        conversation: AssistantConversationEntity,
        user_id: int,
        query: str,
    ) -> list[dict[str, object]]:
        """组装本轮对话上下文：遍历各层依次贡献记忆。

        Args:
            conversation: 会话实体
            user_id: 当前用户ID
            query: 本轮用户输入

        Returns:
            list[dict[str, object]]: 上下文消息列表（调用 SDK 时 cast 为 ChatMessage）
        """
        ctx = MemoryContext(remaining_budget=settings.ai.memory.token_budget)
        for layer in self._layers:
            layer.contribute(ctx, conversation, user_id, query)
        return ctx.messages

    def roll_summary(self, conversation: AssistantConversationEntity) -> None:
        """第 2 层压缩入口（对话结束后调用）。

        Args:
            conversation: 会话实体
        """
        self._summary_layer.consolidate(conversation)
