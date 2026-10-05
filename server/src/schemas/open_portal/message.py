"""开放平台门户：开发者站内信响应模型。"""

from pydantic import BaseModel, Field


class DeveloperMessageResponse(BaseModel):
    """站内信列表项（对齐 web/open_portal 前端 OpenMessage 约定）。"""

    id: int = Field(description="消息 ID")
    title: str = Field(description="消息标题")
    content: str = Field(description="消息正文")
    category: str = Field(description="消息类型：system 系统消息 / audit 审批结果 / notify 业务通知")
    read: bool = Field(description="是否已读")
    created_at: str = Field(description="创建时间（YYYY-MM-DD HH:MM）")


class DeveloperMessageCountResponse(BaseModel):
    """未读消息数。"""

    count: int = Field(description="未读消息数")
