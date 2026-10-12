#!/usr/bin/env python3
"""管理端开放应用审批服务测试（src/services/admin/openapi_app_registration_service.py）。

OpenApiAppRegistrationService 按批次处理开发者创建/修改申请：
    - 查询：申请分页、申请详情
    - 审批通过：create 类置 approved=True；update 类把快照落地到应用表
    - 审批驳回：仅记录意见，应用内容不变
    - 通知：开发者站内信（自助应用）+ 操作者订阅回执（dispatcher）
    - 异常路径：重复审批、申请不存在、关联应用已删除
外部依赖（审批人名称、通知派发、DB session）一律替身。
"""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from src.constants.enums import (
    AppApprovalStatus,
    AppOwnerType,
    AppRegistrationType,
    AppStatus,
)
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.models.entities.developer_message_entity import DeveloperMessageEntity
from src.services.admin.openapi_app_registration_service import OpenApiAppRegistrationService


class FakeSession:
    """记录 add / flush / commit 的会话替身。"""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed: int = 0
        self.committed: int = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1

    def commit(self) -> None:
        self.committed += 1


class FakeRegistrationRepo:
    """申请/审批仓库替身。"""

    def __init__(self, reg: OpenApiAppRegistrationEntity | None = None, app: OpenApiAppEntity | None = None) -> None:
        self.session = FakeSession()
        self._reg = reg
        self._app = app
        # search 返回的 (reg, app) 行
        self.search_rows: list[tuple[OpenApiAppRegistrationEntity, OpenApiAppEntity]] = []
        self.search_total: int = 0

    def get_by_id(self, id: int):
        return self._reg

    def get_app(self, app_id: int):
        return self._app

    def search(self, *, keyword=None, registration_type=None, status=None, skip=0, limit=20):
        return self.search_rows, self.search_total

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()


class FakeAppRepo:
    """应用仓库替身（提供详情与归属方名称解析）。"""

    def __init__(self) -> None:
        self.by_id: dict[int, OpenApiAppEntity] = {}
        self.owner_developer: object | None = SimpleNamespace(name="王开发者", username="dev_wang")
        self.owner_user: object | None = SimpleNamespace(name="李管理员", username="admin_li")

    def get_by_id(self, id: int):
        return self.by_id.get(id)

    def get_owner_developer(self, developer_id: int):
        return self.owner_developer

    def get_owner_user(self, user_id: int):
        return self.owner_user


class FakeDispatcher:
    """记录 dispatch_for_user 调用的通知派发替身。"""

    def __init__(self, *, raise_on_dispatch: bool = False) -> None:
        self.calls: list[dict] = []
        self.raise_on_dispatch = raise_on_dispatch

    def dispatch_for_user(self, **kwargs) -> None:
        if self.raise_on_dispatch:
            raise RuntimeError("模拟派发失败")
        self.calls.append(kwargs)


# ── 实体工厂 ──────────────────────────────────────────


def _make_app(id: int = 1, **overrides) -> OpenApiAppEntity:
    now = datetime.now(UTC)
    kwargs: dict = {
        "id": id,
        "app_id": f"hj_test_{id:04d}",
        "app_key_hash": "x",
        "app_key_encrypted": None,
        "name": f"应用{id}",
        "description": "描述",
        "owner_type": AppOwnerType.DEVELOPER.value,
        "owner_id": 7,
        "approved": False,
        "scopes": "user:read",
        "status": AppStatus.ACTIVE.value,
        "auth_mode": "plain",
        "rate_limit_per_minute": 60,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    kwargs.update(overrides)
    return OpenApiAppEntity(**kwargs)


def _make_registration(id: int = 1, app_id: int = 1, **overrides) -> OpenApiAppRegistrationEntity:
    now = datetime.now(UTC)
    kwargs: dict = {
        "id": id,
        "registration_code": "654321",
        "app_id": app_id,
        "registration_type": AppRegistrationType.CREATE.value,
        "name": "快照应用名",
        "description": "快照描述",
        "scopes": "user:read,order:read",
        "auth_mode": "hmac",
        "apply_reason": "需要权限",
        "status": AppApprovalStatus.PENDING.value,
        "approved_by": None,
        "approval_note": None,
        "approved_at": None,
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return OpenApiAppRegistrationEntity(**kwargs)


def _make_service(reg=None, app=None, dispatcher=None):
    reg_repo = FakeRegistrationRepo(reg=reg, app=app)
    app_repo = FakeAppRepo()
    svc = OpenApiAppRegistrationService(repo=reg_repo, app_repo=app_repo, dispatcher=dispatcher)
    return svc, reg_repo, app_repo


class TestQuery:
    """查询类行为。"""

    def test_list_registrations_pagination(self) -> None:
        """分页查询返回 items/total/page/page_size。"""
        reg = _make_registration()
        app = _make_app()
        svc, reg_repo, _ = _make_service(reg=reg, app=app)
        reg_repo.search_rows = [(reg, app)]
        reg_repo.search_total = 1

        page = svc.list_registrations(page=1, page_size=20)
        assert page["total"] == 1
        assert page["page"] == 1
        assert len(page["items"]) == 1
        # 归属方名称按开发者解析
        assert page["items"][0].owner_name == "王开发者"

    def test_get_registration_success(self) -> None:
        """按申请 ID 查询详情成功。"""
        reg = _make_registration()
        app = _make_app()
        svc, _, _ = _make_service(reg=reg, app=app)

        resp = svc.get_registration(1)
        assert resp.id == 1
        assert resp.app_id_str == app.app_id
        # scopes 快照解析为列表
        assert resp.scopes == ["user:read", "order:read"]

    def test_get_registration_not_found_raises(self) -> None:
        """申请不存在 → NotFoundException。"""
        svc, _, _ = _make_service(reg=None)
        with pytest.raises(NotFoundException):
            svc.get_registration(999)

    def test_get_by_id_uses_to_response(self) -> None:
        """基类通用 get_by_id 经 _to_response 组装响应（admin 归属按用户解析名称）。"""
        reg = _make_registration()
        app = _make_app(owner_type=AppOwnerType.ADMIN.value, owner_id=5)
        svc, _, app_repo = _make_service(reg=reg, app=app)
        app_repo.by_id[1] = app

        resp = svc.get_by_id(1)
        assert resp is not None
        assert resp.owner_name == "李管理员"

    def test_get_by_id_deleted_app_conflict(self) -> None:
        """基类 get_by_id 遇到关联应用已删除 → ConflictException。"""
        reg = _make_registration()
        app = _make_app(deleted_at=datetime.now(UTC))
        svc, _, app_repo = _make_service(reg=reg, app=app)
        app_repo.by_id[1] = app

        with pytest.raises(ConflictException, match="关联应用已被删除"):
            svc.get_by_id(1)


class TestReview:
    """审批动作行为。"""

    def test_approve_create_sets_approved_and_notifies_developer(self) -> None:
        """通过 create 申请：应用 approved 置 True，写开发者站内信，派发操作者回执。"""
        app = _make_app(approved=False)
        reg = _make_registration(registration_type=AppRegistrationType.CREATE.value)
        dispatcher = FakeDispatcher()
        svc, reg_repo, _ = _make_service(reg=reg, app=app, dispatcher=dispatcher)

        resp = svc.review(
            1,
            approved=True,
            note="同意",
            operator={"operator_id": 10, "operator_name": "admin"},
        )

        assert app.approved is True
        assert reg.status == AppApprovalStatus.APPROVED.value
        assert reg.approved_by == 10
        assert reg.approval_note == "同意"
        assert reg.approved_at is not None
        # 开发者站内信
        msgs = [o for o in reg_repo.session.added if isinstance(o, DeveloperMessageEntity)]
        assert len(msgs) == 1
        assert "已通过" in msgs[0].content
        # 操作者回执
        assert len(dispatcher.calls) == 1
        assert dispatcher.calls[0]["user_id"] == 10
        assert resp.status == AppApprovalStatus.APPROVED.value
        # 事务 flush + commit
        assert reg_repo.session.flushed == 1
        assert reg_repo.session.committed == 1

    def test_approve_update_applies_snapshot(self) -> None:
        """通过 update 申请：申请快照整体覆盖应用 name/description/scopes/auth_mode。"""
        app = _make_app(name="旧名", description="旧描述", scopes="user:read", auth_mode="plain", approved=True)
        reg = _make_registration(
            registration_type=AppRegistrationType.UPDATE.value,
            name="新名",
            description="新描述",
            scopes="order:write",
            auth_mode="hmac",
        )
        svc, _, _ = _make_service(reg=reg, app=app)

        svc.review(1, approved=True, operator={"operator_id": 10})
        assert app.name == "新名"
        assert app.description == "新描述"
        assert app.scopes == "order:write"
        assert app.auth_mode == "hmac"

    def test_reject_notifies_developer_and_keeps_app(self) -> None:
        """驳回：应用内容不变，写驳回站内信。"""
        app = _make_app(approved=False)
        reg = _make_registration(registration_type=AppRegistrationType.CREATE.value)
        svc, reg_repo, _ = _make_service(reg=reg, app=app)

        svc.review(1, approved=False, note="材料不齐", operator={"operator_id": 10})

        assert reg.status == AppApprovalStatus.REJECTED.value
        assert app.approved is False  # 驳回不改变应用
        msgs = [o for o in reg_repo.session.added if isinstance(o, DeveloperMessageEntity)]
        assert "未通过" in msgs[0].content
        assert "材料不齐" in msgs[0].content

    def test_review_non_pending_conflict(self) -> None:
        """重复审批（已非 pending）→ ConflictException，且不写站内信。"""
        app = _make_app()
        reg = _make_registration(status=AppApprovalStatus.APPROVED.value)
        svc, reg_repo, _ = _make_service(reg=reg, app=app)

        with pytest.raises(ConflictException, match="已被处理"):
            svc.review(1, approved=True, operator={"operator_id": 10})
        assert reg_repo.session.added == []

    def test_review_deleted_app_conflict(self) -> None:
        """关联应用已软删 → ConflictException。"""
        app = _make_app(deleted_at=datetime.now(UTC))
        reg = _make_registration()
        svc, _, _ = _make_service(reg=reg, app=app)

        with pytest.raises(ConflictException, match="关联应用已被删除"):
            svc.review(1, approved=True, operator={"operator_id": 10})

    def test_review_admin_owned_skips_developer_message(self) -> None:
        """admin 归属应用审批 → 不写开发者站内信。"""
        app = _make_app(owner_type=AppOwnerType.ADMIN.value, owner_id=5)
        reg = _make_registration()
        svc, reg_repo, _ = _make_service(reg=reg, app=app)

        svc.review(1, approved=True, operator={"operator_id": 10})
        assert not any(isinstance(o, DeveloperMessageEntity) for o in reg_repo.session.added)

    def test_review_without_operator_id_skips_dispatch(self) -> None:
        """操作者 ID 缺失 → 不派发订阅回执。"""
        app = _make_app()
        reg = _make_registration()
        dispatcher = FakeDispatcher()
        svc, _, _ = _make_service(reg=reg, app=app, dispatcher=dispatcher)

        svc.review(1, approved=True, operator=None)
        assert dispatcher.calls == []

    def test_dispatch_failure_does_not_break_review(self) -> None:
        """通知派发抛异常 → 不阻断审批主流程。"""
        app = _make_app()
        reg = _make_registration()
        dispatcher = FakeDispatcher(raise_on_dispatch=True)
        svc, _, _ = _make_service(reg=reg, app=app, dispatcher=dispatcher)

        # 派发失败被内部捕获，审批结果照常返回
        resp = svc.review(1, approved=True, operator={"operator_id": 10})
        assert resp.status == AppApprovalStatus.APPROVED.value
