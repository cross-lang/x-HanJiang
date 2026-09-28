#!/usr/bin/env python3
"""AI 助手请求 / 响应模型。

统一存放 AI 助手模块的接口入参与出参 Pydantic 模型，供 api 层使用。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """AI 助手对话请求。

    Attributes:
        conversation_id: 会话ID（为空则自动创建新会话）
        message: 用户输入内容
    """

    conversation_id: int | None = Field(default=None, description="会话ID；为空则创建新会话")
    message: str = Field(min_length=1, max_length=4000, description="用户输入")


class FeedbackRequest(BaseModel):
    """AI 助手消息反馈请求。

    Attributes:
        conversation_id: 会话ID
        message_id: 被反馈的消息ID（取自 done 事件）
        positive: 是否好评
        comment: 补充意见（可空）
    """

    conversation_id: int = Field(description="会话ID")
    message_id: int = Field(description="被反馈的消息ID")
    positive: bool = Field(description="是否好评：true 好评 / false 差评")
    comment: str | None = Field(default=None, max_length=500, description="补充意见")


class ConversationResponse(BaseModel):
    """会话响应模型。

    Attributes:
        id: 会话ID
        user_id: 所属用户ID
        summary: 滚动摘要（可空）
        is_pinned: 是否置顶
        created_at: 创建时间
        updated_at: 更新时间
    """

    id: int = Field(description="会话ID")
    user_id: int = Field(description="所属用户ID")
    summary: str | None = Field(default=None, description="滚动摘要")
    is_pinned: bool = Field(default=False, description="是否置顶")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    model_config = ConfigDict(from_attributes=True)


class ConversationPinRequest(BaseModel):
    """会话置顶请求。

    Attributes:
        pinned: True 置顶 / False 取消置顶
    """

    pinned: bool = Field(description="是否置顶：true 置顶 / false 取消置顶")


class MessageResponse(BaseModel):
    """会话消息响应模型。

    Attributes:
        id: 消息ID
        conversation_id: 所属会话ID
        role: 消息角色（user / assistant）
        content: 消息内容
        created_at: 创建时间
    """

    id: int = Field(description="消息ID")
    conversation_id: int = Field(description="所属会话ID")
    role: str = Field(description="消息角色")
    content: str = Field(description="消息内容")
    created_at: datetime = Field(description="创建时间")
    model_config = ConfigDict(from_attributes=True)
