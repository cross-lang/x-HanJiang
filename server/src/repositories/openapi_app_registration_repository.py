#!/usr/bin/env python3
"""开放平台应用申请表数据访问（申请批次 / 审批查询）。"""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult

from src.constants.enums import AppApprovalStatus
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.repositories.base_repository import BaseRepository


class OpenApiAppRegistrationRepository(BaseRepository[OpenApiAppRegistrationEntity, int]):
    """OpenApiAppRegistration 数据访问，支撑审批列表与审批动作。"""

    model_class = OpenApiAppRegistrationEntity

    def search(
        self,
        keyword: str | None = None,
        registration_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[OpenApiAppRegistrationEntity, OpenApiAppEntity]], int]:
        """分页查询申请记录（联查应用主表，按申请ID倒序）。

        仅返回应用未软删除的记录；keyword 同时匹配应用对外 App ID / 应用名
        （应用表与申请快照名均参与匹配）。审批列表由 service 层基于
        (申请实体, 应用实体) 对二次组装展示信息。

        Returns:
            ((申请实体, 应用实体) 列表, 匹配总数)
        """
        base = select(OpenApiAppRegistrationEntity, OpenApiAppEntity).join(
            OpenApiAppEntity, OpenApiAppEntity.id == OpenApiAppRegistrationEntity.app_id
        )
        base = base.where(OpenApiAppEntity.deleted_at.is_(None))
        if registration_type:
            base = base.where(OpenApiAppRegistrationEntity.registration_type == registration_type)
        if status:
            base = base.where(OpenApiAppRegistrationEntity.status == status)
        if keyword:
            kw = f"%{keyword}%"
            base = base.where(
                or_(
                    OpenApiAppEntity.app_id.like(kw),
                    OpenApiAppEntity.name.like(kw),
                    OpenApiAppRegistrationEntity.name.like(kw),
                )
            )
        total = self.session.execute(
            select(func.count(func.distinct(OpenApiAppRegistrationEntity.id))).select_from(base.subquery())
        ).scalar_one()
        stmt = base.order_by(OpenApiAppRegistrationEntity.id.desc()).offset(skip).limit(limit)
        rows = self.session.execute(stmt).all()
        return [(r[0], r[1]) for r in rows], total

    def get_by_id(self, id: int) -> OpenApiAppRegistrationEntity | None:
        """按申请ID查询（含全量历史记录，不做软删过滤）。"""
        return self.session.get(OpenApiAppRegistrationEntity, id)

    def code_exists(self, code: str) -> bool:
        """判断申请码是否已被占用（生成申请码时查重用）。"""
        stmt = select(OpenApiAppRegistrationEntity.id).where(
            OpenApiAppRegistrationEntity.registration_code == code
        )
        return self.session.execute(stmt).first() is not None

    def find_pending_by_app(self, app_id: int) -> OpenApiAppRegistrationEntity | None:
        """查询指定应用当前待审批的申请记录（同一应用同一时刻至多一条 pending）。"""
        stmt = select(OpenApiAppRegistrationEntity).where(
            OpenApiAppRegistrationEntity.app_id == app_id,
            OpenApiAppRegistrationEntity.status == "pending",
        )
        return self.session.execute(stmt).scalars().first()

    def reject_pending_by_app_ids(self, app_ids: list[int], note: str) -> int:
        """批量驳回指定应用集合下的全部待审批申请。

        用于"禁用开发者账号"级联场景：开发者账号被禁用时，
        其名下应用待审批的申请批次一并驳回，避免申请悬空。

        Args:
            app_ids: 应用 ID 列表
            note: 驳回原因（写入 approval_note）

        Returns:
            int: 受影响行数
        """
        if not app_ids:
            return 0
        stmt = (
            update(OpenApiAppRegistrationEntity)
            .where(
                OpenApiAppRegistrationEntity.app_id.in_(app_ids),
                OpenApiAppRegistrationEntity.status == "pending",
            )
            .values(
                status=AppApprovalStatus.REJECTED.value,
                approval_note=note,
                approved_at=datetime.now(),
            )
        )
        result = cast("CursorResult[Any]", self.session.execute(stmt))
        return result.rowcount or 0

    def find_latest_by_app(self, app_id: int) -> OpenApiAppRegistrationEntity | None:
        """查询指定应用最近一条申请记录（用于门户端派生最近审批结果）。"""
        stmt = (
            select(OpenApiAppRegistrationEntity)
            .where(OpenApiAppRegistrationEntity.app_id == app_id)
            .order_by(OpenApiAppRegistrationEntity.id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def get_app(self, app_id: int) -> OpenApiAppEntity | None:
        """按应用ID查询应用主表记录（组装审批列表展示信息用）。"""
        return self.session.get(OpenApiAppEntity, app_id)

    def list_by_app(self, app_id: int) -> list[OpenApiAppRegistrationEntity]:
        """查询指定应用的全部申请/审批记录（最新在前，含终态与待审批批次）。

        供"应用审批记录"入口使用：每次创建/修改申请均为一条批次，
        审批结果（approved_by / approval_note / approved_at）随批次留痕。
        """
        stmt = (
            select(OpenApiAppRegistrationEntity)
            .where(OpenApiAppRegistrationEntity.app_id == app_id)
            .order_by(OpenApiAppRegistrationEntity.id.desc())
        )
        return list(self.session.execute(stmt).scalars().all())
