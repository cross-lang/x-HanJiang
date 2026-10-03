"""公告相关数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.constants.enums import AnnouncementContentType, AnnouncementPosition


class AnnouncementCreateRequest(BaseModel):
    """公告创建请求模型（创建后为草稿状态）。

    Attributes:
        title: 公告标题（1-200 字）
        content: 公告正文（1-20000 字）
        content_type: 正文格式（markdown/richtext）
        position: 展示位置（board 首页板块 / banner 首页横幅）
        start_at: 生效开始时间
        end_at: 生效结束时间
        sort_order: 展示排序（越小越靠前）
    """

    title: str = Field(min_length=1, max_length=200, description="公告标题")
    content: str = Field(min_length=1, max_length=20000, description="公告正文")
    content_type: AnnouncementContentType = Field(
        default=AnnouncementContentType.MARKDOWN,
        description="正文格式（markdown/richtext）",
    )
    position: AnnouncementPosition = Field(default=AnnouncementPosition.BOARD, description="展示位置（board/banner）")
    start_at: datetime = Field(description="生效开始时间")
    end_at: datetime = Field(description="生效结束时间")
    sort_order: int = Field(default=0, ge=0, description="展示排序（越小越靠前）")

    @model_validator(mode="after")
    def _validate_period(self) -> AnnouncementCreateRequest:
        """校验有效期：结束时间必须晚于开始时间。"""
        if self.end_at <= self.start_at:
            raise ValueError("生效结束时间必须晚于开始时间")
        return self


class AnnouncementUpdateRequest(BaseModel):
    """公告修改请求模型（所有字段可选，仅更新提供的字段）。"""

    title: str | None = Field(default=None, min_length=1, max_length=200, description="公告标题")
    content: str | None = Field(default=None, min_length=1, max_length=20000, description="公告正文")
    content_type: AnnouncementContentType | None = Field(default=None, description="正文格式")
    position: AnnouncementPosition | None = Field(default=None, description="展示位置")
    start_at: datetime | None = Field(default=None, description="生效开始时间")
    end_at: datetime | None = Field(default=None, description="生效结束时间")
    sort_order: int | None = Field(default=None, ge=0, description="展示排序")

    @model_validator(mode="after")
    def _validate_period(self) -> AnnouncementUpdateRequest:
        """校验有效期：仅当两者都提供时要求结束晚于开始。"""
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("生效结束时间必须晚于开始时间")
        return self


class AnnouncementResponse(BaseModel):
    """公告响应模型。"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="公告 ID")
    title: str = Field(description="公告标题")
    content: str = Field(description="公告正文")
    content_type: str = Field(description="正文格式（markdown/richtext）")
    position: str = Field(description="展示位置（board/banner）")
    status: str = Field(description="发布状态（draft/published/unpublished）")
    start_at: datetime | None = Field(default=None, description="生效开始时间")
    end_at: datetime | None = Field(default=None, description="生效结束时间")
    sort_order: int = Field(default=0, description="展示排序")
    operator_id: int | None = Field(default=None, description="操作人用户 ID")
    operator_name: str | None = Field(default=None, description="操作人用户名")
    published_at: datetime | None = Field(default=None, description="发布时间")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")
    is_expired: bool = Field(default=False, description="是否已过期（发布中但已过有效期）")
