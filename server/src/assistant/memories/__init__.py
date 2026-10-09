#!/usr/bin/env python3
"""记忆系统：四层记忆的类封装与统一编排。

TL;DR —— 本包做什么：
    给 AI 助手每轮对话拼装「上下文消息列表」交给 LLM。上下文由四层
    记忆按优先级依次贡献，超出 token 预算的旧消息会被压缩进摘要。

如何使用（入口在 MemoryFacade）：
    # 1. 每轮对话开始前，组装上下文：
    memory_facade.build_context(conversation, user_id, query)
    # 2. 对话结束、回复落库后触发摘要压缩：
    memory_facade.roll_summary(conversation)

四层结构（每层一个内聚类，MemoryFacade 只做编排）：
    L0 系统提示词   SystemPromptLayer    永不丢弃；身份/系统入口路由表/FAQ
    L1 长期记忆     UserLongTermMemory   跨会话用户档案
    L2 滚动摘要     SummaryMemoryLayer   窗口外旧消息渐进压缩进 Conversation.summary
    L3 最近 N 轮    RecentMemoryLayer    精确保留最近几轮原文，超预算从最旧丢弃

核心抽象：
    - MemoryLayer.contribute(ctx, ...)：各层向 ctx 追加消息并扣减预算
    - MemoryContext：层间传递的「消息 + 剩余预算 + 本轮动态内容」黑板
    - MemoryFacade.build_context() / roll_summary()：组装与压缩入口

依赖倒置：各层只面向 ports.py 的 Protocol 端口（MessageRepository /
ConversationRepository），不依赖具体仓储；SystemPromptBuilder / ORM
实体仅在 TYPE_CHECKING 下导入，运行时零循环导入。

数据流（build_context 内部）：
    ┌─────────────┐  contribute   ┌──────────────┐
    │ L0 提示词层   │ ───────────▶  │              │ 注入 system 提示词
    └─────────────┘               │              │ 并 charge 其 token
    ┌─────────────┐  contribute   │ MemoryContext│
    │ L2 摘要层    │ ───────────▶  │  .messages   │ 注入「历史摘要」
    └─────────────┘               │  .remaining_ │ （无摘要则跳过）
    ┌─────────────┐  contribute   │   budget     │
    │ L3 原文层    │ ───────────▶  │              │ 在剩余预算内从新
    └─────────────┘               └──────────────┘ 到旧贪心选原文
           │
           ▼ 对话结束、回复落库后
    MemoryFacade.roll_summary → L2.consolidate：把窗口外最旧消息 LLM 压缩进
    Conversation.summary 并删除原文（L2 的「写入/沉淀」反向操作）

模块导引：
    「某层干什么」       → 对应 *Layer 类所在模块的 docstring
    「层如何被驱动」     → base.py（MemoryLayer）+ facade.py（MemoryFacade）
    「层之间传什么」     → base.py（MemoryContext）
    「数据从哪来」       → ports.py（存储端口 Protocol）
    「提示词/FAQ 静态知识」→ knowledge.py（SystemPromptBuilder）
"""

from src.assistant.memories.base import MemoryContext, MemoryLayer
from src.assistant.memories.facade import MemoryFacade
from src.assistant.memories.knowledge import (
    FaqItem,
    PromptTemplate,
    SystemPromptBuilder,
    default_faq_path,
    default_prompt_path,
    load_assistant_faq,
    load_prompt_template,
)
from src.assistant.memories.long_term import (
    DbUserLongTermMemory,
    NullUserLongTermMemory,
    UserLongTermMemory,
    build_user_long_term_memory,
)
from src.assistant.memories.ports import (
    ConversationRepository,
    Message,
    MessageRepository,
    UserProfileRepository,
)
from src.assistant.memories.recent import RecentMemoryLayer
from src.assistant.memories.summary import SummaryMemoryLayer
from src.assistant.memories.system_prompt import SystemPromptLayer

__all__ = [
    # 端口与基础抽象
    "Message",
    "MessageRepository",
    "ConversationRepository",
    "UserProfileRepository",
    "MemoryContext",
    "MemoryLayer",
    # 四层记忆
    "SystemPromptLayer",
    "UserLongTermMemory",
    "NullUserLongTermMemory",
    "DbUserLongTermMemory",
    "build_user_long_term_memory",
    "SummaryMemoryLayer",
    "RecentMemoryLayer",
    # 编排门面
    "MemoryFacade",
    # 静态知识库
    "SystemPromptBuilder",
    "FaqItem",
    "PromptTemplate",
    "load_assistant_faq",
    "default_faq_path",
    "load_prompt_template",
    "default_prompt_path",
]
