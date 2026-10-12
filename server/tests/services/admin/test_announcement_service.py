#!/usr/bin/env python3
"""公告业务服务单元测试。

覆盖 src/services/admin/announcement_service.py：
    - 创建草稿 / 修改 / 删除
    - 发布：已是发布态冲突 / 未设有效期 / 结束早于开始 / 已过期 / 成功
    - 下架：非发布态冲突 / 成功
    - 查询：分页 / 详情 / 首页生效公告

数据访问用内存 FakeAnnouncementRepository 替身，不连真实 DB；审计切面由
conftest 自动降级为 no-op。
"""

from datetime import datetime, timedelta

import pytest
from src.constants.enums import AnnouncementStatus
from src.core.exceptions import ConflictException, NotFoundException, ValidationException
from src.models.entities.announcement_entity import AnnouncementEntity
from src.schemas.admin.announcement import AnnouncementCreateRequest, AnnouncementUpdateRequest
from src.services.admin.announcement_service import AnnouncementService


def _future_window(days_ahead: int = 7) -> tuple[datetime, datetime]:
    """生成一段未来有效期（naive 时间，与 DB 列及服务端 datetime.now() 对齐）。"""
    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(days=days_ahead)
    return start, end


class FakeAnnouncementRepository:
    """内存版公告仓库替身。"""

    def __init__(self) -> None:
        self._items: dict[int, AnnouncementEntity] = {}
        self._next_id = 1

    def create(self, entity: AnnouncementEntity) -> AnnouncementEntity:
        entity.id = self._next_id
        self._next_id += 1
        self._items[entity.id] = entity
        return entity

    def get_by_id(self, announcement_id: int) -> AnnouncementEntity | None:
        return self._items.get(announcement_id)

    def search(self, status=None, position=None, keyword=None, skip=0, limit=20):
        rows = list(self._items.values())
        total = len(rows)
        return rows[skip : skip + limit], total

    def list_available(self, position=None, limit=20):
        now = datetime.now()
        return [
            a
            for a in self._items.values()
            if a.status == AnnouncementStatus.PUBLISHED.value
            and a.start_at
            and a.end_at
            and a.start_at <= now <= a.end_at
        ][:limit]

    def delete(self, announcement_id: int) -> None:
        self._items.pop(announcement_id, None)

    def commit(self) -> None:
        return None


class TestAnnouncementService:
    """公告服务行为。"""

    def setup_method(self) -> None:
        self.repo = FakeAnnouncementRepository()
        self.service = AnnouncementService(repository=self.repo)

    def _create_draft(self, title: str = "维护公告") -> AnnouncementEntity:
        start, end = _future_window()
        req = AnnouncementCreateRequest(title=title, content="正文", start_at=start, end_at=end)
        return self.service.create(req, operator={"operator_id": 1})

    # ── 创建 ────────────────────────────────────────────

    def test_create_draft(self) -> None:
        """创建后初始为草稿状态。"""
        entity = self._create_draft()
        assert entity.id == 1
        assert entity.status == AnnouncementStatus.DRAFT.value
        assert entity.title == "维护公告"

    # ── 修改 / 删除 ──────────────────────────────────────

    def test_update_existing(self) -> None:
        """修改存在的公告字段。"""
        entity = self._create_draft()
        req = AnnouncementUpdateRequest(title="新标题")
        updated = self.service.update(entity.id, req, operator={"operator_id": 1})
        assert updated.title == "新标题"

    def test_update_missing_raises_not_found(self) -> None:
        """修改不存在的公告 → NotFoundException。"""
        with pytest.raises(NotFoundException):
            self.service.update(999, AnnouncementUpdateRequest(title="x"))

    def test_delete_existing(self) -> None:
        """删除存在的公告。"""
        entity = self._create_draft()
        assert self.service.delete(entity.id) is True
        assert self.repo.get_by_id(entity.id) is None

    def test_delete_missing_raises_not_found(self) -> None:
        """删除不存在的公告 → NotFoundException。"""
        with pytest.raises(NotFoundException):
            self.service.delete(999)

    # ── 发布 ────────────────────────────────────────────

    def test_publish_success(self) -> None:
        """草稿且有效期合法 → 发布成功。"""
        entity = self._create_draft()
        published = self.service.publish(entity.id)
        assert published.status == AnnouncementStatus.PUBLISHED.value
        assert published.published_at is not None

    def test_publish_already_published_conflict(self) -> None:
        """已是发布态 → ConflictException。"""
        entity = self._create_draft()
        self.service.publish(entity.id)
        with pytest.raises(ConflictException):
            self.service.publish(entity.id)

    def test_publish_missing_period_validation(self) -> None:
        """未设有效期 → ValidationException。"""
        entity = self._create_draft()
        entity.start_at = None  # 人为抹掉有效期
        with pytest.raises(ValidationException):
            self.service.publish(entity.id)

    def test_publish_end_not_after_start_validation(self) -> None:
        """结束不晚于开始 → ValidationException。"""
        entity = self._create_draft()
        entity.end_at = entity.start_at  # 结束 == 开始
        with pytest.raises(ValidationException):
            self.service.publish(entity.id)

    def test_publish_expired_validation(self) -> None:
        """有效期已结束 → ValidationException。"""
        entity = self._create_draft()
        past = datetime.now() - timedelta(days=2)
        entity.start_at = past - timedelta(days=2)
        entity.end_at = past
        with pytest.raises(ValidationException):
            self.service.publish(entity.id)

    # ── 下架 ────────────────────────────────────────────

    def test_unpublish_success(self) -> None:
        """已发布 → 下架成功。"""
        entity = self._create_draft()
        self.service.publish(entity.id)
        unpublished = self.service.unpublish(entity.id)
        assert unpublished.status == AnnouncementStatus.UNPUBLISHED.value

    def test_unpublish_non_published_conflict(self) -> None:
        """非发布态 → ConflictException。"""
        entity = self._create_draft()
        with pytest.raises(ConflictException):
            self.service.unpublish(entity.id)

    # ── 查询 ────────────────────────────────────────────

    def test_list_pagination(self) -> None:
        """分页查询返回结构正确。"""
        for i in range(3):
            self._create_draft(title=f"公告{i}")
        result = self.service.list(page=1, page_size=2)
        assert result["total"] == 3
        assert len(result["items"]) == 2
        assert result["total_pages"] == 2

    def test_get_existing(self) -> None:
        entity = self._create_draft()
        assert self.service.get(entity.id).id == entity.id

    def test_get_missing_raises_not_found(self) -> None:
        with pytest.raises(NotFoundException):
            self.service.get(999)

    def test_list_available_only_published_in_window(self) -> None:
        """首页生效公告：仅返回已发布且在有效期内的。"""
        draft = self._create_draft("草稿")
        published = self._create_draft("已发布")
        # 调整为当前正处于有效期内（开始在过去、结束在未来）
        published.start_at = datetime.now() - timedelta(days=1)
        published.end_at = datetime.now() + timedelta(days=7)
        self.service.publish(published.id)
        result = self.service.list_available()
        ids = {a.id for a in result}
        assert published.id in ids
        assert draft.id not in ids
