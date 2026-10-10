#!/usr/bin/env python3
"""AI 助手会话数据实体。

纯数据模型定义：只声明字段、索引与关联关系，禁止写入业务逻辑。
三张表：
    - assistant_conversations: 会话（含第 2 层记忆的滚动摘要字段 summary）
    - assistant_messages:      会话消息（仅持久化 user / assistant 角色）
    - assistant_feedbacks:     用户对消息质量的 👍👎 反馈（提示词调优数据源）
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class AssistantConversationEntity(Base):
    """AI 助手会话表实体。"""

    __tablename__ = "assistant_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属用户ID")
    title: Mapped[str | None] = mapped_column(String(60), nullable=True, comment="会话主题名（AI 自动归纳，页面展示）")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="滚动摘要（第2层记忆，压缩远历史）")
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("0"), default=False, comment="是否置顶"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None, comment="软删除时间（NULL 表示未删除）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="更新时间",
    )
    __table_args__ = (Index("idx_assistant_conv_user", "user_id"),)


class AssistantMessageEntity(Base):
    """AI 助手会话消息表实体。"""

    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属会话ID",
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="消息角色：user/assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    __table_args__ = (Index("idx_assistant_msg_conv", "conversation_id"),)


class AssistantFeedbackEntity(Base):
    """AI 助手消息反馈表实体。"""

    __tablename__ = "assistant_feedbacks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话ID",
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="被反馈的消息ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="反馈用户ID")
    positive: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否好评：true 好评 / false 差评")
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="补充意见")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    __table_args__ = (Index("idx_assistant_feedback_conv", "conversation_id"),)


class AssistantUserProfileEntity(Base):
    """AI 助手用户长期档案表实体（第 1 层记忆持久化）。

    一个用户一条档案，由 LLM 从历史对话中定期抽取更新，跨会话沉淀。
    """

    __tablename__ = "assistant_user_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属用户ID")
    profile: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户档案文本（LLM 抽取沉淀）")
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
        comment="版本号（乐观锁，防并发抽取覆盖）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="更新时间",
    )
    __table_args__ = (Index("uk_assistant_profile_user", "user_id", unique=True),)
