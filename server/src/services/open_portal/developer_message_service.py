#!/usr/bin/env python3
"""开发者站内信服务（开放平台门户域）。
仅调用 DeveloperMessageRepository 存取数据，不直接操作数据库会话。
与管理系统用户站内信（StationMessageService + station_messages）分表隔离。
"""

from src.constants.enums import DeveloperMessageCategory, DeveloperMessageStatus
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.repositories.developer_message_repository import DeveloperMessageRepository


class DeveloperMessageService:
    """开发者站内信服务。"""

    def __init__(self, repository: DeveloperMessageRepository) -> None:
        self._repository = repository

    def unread_count(self, developer_id: int) -> int:
        return self._repository.unread_count(developer_id)

    def list_messages(self, developer_id: int, page: int, page_size: int) -> dict:
        skip = (page - 1) * page_size
        rows, total = self._repository.list_messages(
            developer_id=developer_id, skip=skip, limit=page_size
        )
        items = [
            {
                "id": r.id,
                "title": r.title,
                "content": r.content,
                "category": r.category,
                "read": r.status == DeveloperMessageStatus.READ.value,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]
        return {"total": total, "items": items}

    def mark_read(self, developer_id: int, msg_id: int) -> None:
        msg = self._repository.get_message(developer_id, msg_id)
        if msg:
            self._repository.mark_read(msg)
            self._repository.commit()

    def mark_all_read(self, developer_id: int) -> None:
        self._repository.mark_all_read(developer_id)
        self._repository.commit()

    def send(
        self,
        developer_id: int,
        title: str,
        content: str,
        category: DeveloperMessageCategory = DeveloperMessageCategory.SYSTEM,
    ) -> None:
        """发送站内信给指定开发者（经仓库）。

        预留：后续审批结果、系统通知等场景（如应用 scope 审批通过/驳回）调用，
        开发者门户右上角铃铛即时可见。

        Args:
            developer_id: 目标开发者 ID（developers.id）
            title: 站内信标题
            content: 站内信正文
            category: 消息类型（默认 system）
        """
        msg = DeveloperMessageEntity(
            developer_id=developer_id,
            title=title,
            content=content,
            category=category.value,
            status=DeveloperMessageStatus.UNREAD.value,
        )
        self._repository.create(msg)
        self._repository.commit()
