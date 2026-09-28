"""公告业务逻辑层。
负责公告的创建、修改、删除、发布、下架、列表与详情，
以及首页生效公告的查询。数据访问仅经 AnnouncementRepository。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.constants.enums import AnnouncementStatus
from src.core.exceptions import ConflictException, NotFoundException, ValidationException
from src.core.logger import logger
from src.models.entities.announcement_entity import AnnouncementEntity
from src.repositories.announcement_repository import AnnouncementRepository
from src.schemas.announcement import AnnouncementCreateRequest, AnnouncementUpdateRequest


class AnnouncementService:
    """公告业务逻辑实现。"""

    def __init__(self, repository: AnnouncementRepository) -> None:
        self._repository = repository

    # ── 创建 / 修改 / 删除 ────────────────────────────────

    def create(
        self,
        request: AnnouncementCreateRequest,
        operator: dict[str, Any] | None = None,
    ) -> AnnouncementEntity:
        """创建公告（初始为草稿状态）。

        Args:
            request: 创建请求
            operator: 操作人上下文

        Returns:
            AnnouncementEntity: 新建公告实体
        """
        now = datetime.now()
        entity = AnnouncementEntity(
            title=request.title,
            content=request.content,
            content_type=request.content_type.value,
            position=request.position.value,
            status=AnnouncementStatus.DRAFT.value,
            start_at=request.start_at,
            end_at=request.end_at,
            sort_order=request.sort_order,
            operator_id=operator.get("operator_id") if operator else None,
            operator_name=operator.get("operator_name") if operator else None,
            created_at=now,
        )
        entity = self._repository.create(entity)
        self._repository.commit()
        logger.info("Announcement created: id=%s title=%s", entity.id, entity.title)
        return entity

    def update(
        self,
        announcement_id: int,
        request: AnnouncementUpdateRequest,
        operator: dict[str, Any] | None = None,
    ) -> AnnouncementEntity:
        """修改公告信息。

        Args:
            announcement_id: 公告 ID
            request: 修改请求
            operator: 操作人上下文

        Returns:
            AnnouncementEntity: 更新后的公告实体

        Raises:
            NotFoundException: 公告不存在时抛出
        """
        entity = self._get_entity(announcement_id)
        patch_data = request.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in patch_data.items():
            if hasattr(entity, key) and value is not None:
                setattr(entity, key, value.value if hasattr(value, "value") else value)
        entity.updated_at = datetime.now()
        self._repository.commit()
        logger.info("Announcement updated: id=%s", announcement_id)
        return entity

    def delete(self, announcement_id: int, operator: dict[str, Any] | None = None) -> None:
        """删除公告（物理删除）。

        Args:
            announcement_id: 公告 ID
            operator: 操作人上下文

        Raises:
            NotFoundException: 公告不存在时抛出
        """
        entity = self._get_entity(announcement_id)
        self._repository.delete(announcement_id)
        self._repository.commit()
        logger.info(
            "Announcement deleted: id=%s title=%s operator=%s",
            announcement_id,
            entity.title,
            operator.get("operator_name") if operator else None,
        )

    # ── 发布 / 下架 ───────────────────────────────────────

    def publish(self, announcement_id: int, operator: dict[str, Any] | None = None) -> AnnouncementEntity:
        """发布公告（草稿/已下架 → 已发布），校验有效期。

        Args:
            announcement_id: 公告 ID
            operator: 操作人上下文

        Returns:
            AnnouncementEntity: 发布后的公告实体

        Raises:
            NotFoundException: 公告不存在时抛出
            ValidationException: 有效期非法或已过期时抛出
            ConflictException: 已是发布状态时抛出
        """
        entity = self._get_entity(announcement_id)
        if entity.status == AnnouncementStatus.PUBLISHED.value:
            raise ConflictException(message="公告已是发布状态")
        now = datetime.now()
        if entity.start_at is None or entity.end_at is None:
            raise ValidationException(message="公告必须设置有效期后才能发布")
        if entity.end_at <= entity.start_at:
            raise ValidationException(message="生效结束时间必须晚于开始时间")
        if entity.end_at < now:
            raise ValidationException(message="公告有效期已结束，无法发布")
        entity.status = AnnouncementStatus.PUBLISHED.value
        entity.published_at = now
        entity.updated_at = now
        self._repository.commit()
        logger.info("Announcement published: id=%s", announcement_id)
        return entity

    def unpublish(self, announcement_id: int, operator: dict[str, Any] | None = None) -> AnnouncementEntity:
        """下架公告（已发布 → 已下架）。

        Args:
            announcement_id: 公告 ID
            operator: 操作人上下文

        Returns:
            AnnouncementEntity: 下架后的公告实体

        Raises:
            NotFoundException: 公告不存在时抛出
            ConflictException: 非发布状态时抛出
        """
        entity = self._get_entity(announcement_id)
        if entity.status != AnnouncementStatus.PUBLISHED.value:
            raise ConflictException(message="仅已发布公告可下架")
        entity.status = AnnouncementStatus.UNPUBLISHED.value
        entity.updated_at = datetime.now()
        self._repository.commit()
        logger.info("Announcement unpublished: id=%s", announcement_id)
        return entity

    # ── 查询 ─────────────────────────────────────────────

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        position: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        """分页查询公告（管理视角，含草稿/已下架）。

        Args:
            page: 页码
            page_size: 每页数量
            status: 发布状态过滤
            position: 展示位置过滤
            keyword: 标题/正文关键字过滤

        Returns:
            dict[str, Any]: 包含 items（实体列表）、total、page、page_size、total_pages 的分页结果
        """
        skip = (page - 1) * page_size
        items, total = self._repository.search(
            status=status,
            position=position,
            keyword=keyword,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }

    def get(self, announcement_id: int) -> AnnouncementEntity:
        """查询公告详情。

        Args:
            announcement_id: 公告 ID

        Returns:
            AnnouncementEntity: 公告实体

        Raises:
            NotFoundException: 公告不存在时抛出
        """
        return self._get_entity(announcement_id)

    def list_available(self, position: str | None = None, limit: int = 20) -> list[AnnouncementEntity]:
        """查询首页生效公告（已发布且在有效期内）。

        Args:
            position: 展示位置过滤（可选）
            limit: 返回条数上限

        Returns:
            list[AnnouncementEntity]: 生效公告列表
        """
        return self._repository.list_available(position=position, limit=limit)

    # ── 内部工具 ──────────────────────────────────────────

    def _get_entity(self, announcement_id: int) -> AnnouncementEntity:
        entity = self._repository.get_by_id(announcement_id)
        if entity is None:
            raise NotFoundException(message="公告不存在")
        return entity
