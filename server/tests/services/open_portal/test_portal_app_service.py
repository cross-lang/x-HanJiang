#!/usr/bin/env python3
"""开放门户开发者应用管理服务测试（src/services/open_portal/app_service.py）。

DeveloperOpenApiAppService 全部写操作走"申请-审批"流：
    - 查询：我的应用分页、应用详情、scope 目录、审批历史
    - 创建：同名冲突 / 非法鉴权模式 / 通知审批人
    - 修改/申请权限：存在 pending 申请时 409
    - 密钥：重置、一次性查看（未审批 / 已查看 / 密文异常分支）
    - 删除：软删并把 pending 申请作废
外部存储（session.execute）以 FakeSession 替身，不连真实 DB。
"""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from src.constants.enums import AppApprovalStatus, AppOwnerType, AppRegistrationType, AppStatus
from src.core.exceptions import ConflictException, NotFoundException, ValidationException
from src.models.entities.app_entity import OpenApiAppEntity
from src.models.entities.app_registration_entity import OpenApiAppRegistrationEntity
from src.models.entities.station_message_entity import StationMessageEntity
from src.schemas.open_portal.app import (
    OpenAppCreateRequest,
    OpenAppScopeApplyRequest,
    OpenAppUpdateRequest,
)
from src.services.open_portal.app_service import DeveloperOpenApiAppService

# ── 内存替身 ──────────────────────────────────────────


class _FakeScalarResult:
    """模拟 session.execute(...).scalars() 的返回对象。"""

    def __init__(self, items: list) -> None:
        self._items = items

    def all(self) -> list:
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class _FakeExecuteResult:
    """模拟 session.execute() 的返回对象（仅暴露 scalars 链式调用）。"""

    def __init__(self, items: list) -> None:
        self._scalars = _FakeScalarResult(items)

    def scalars(self) -> _FakeScalarResult:
        return self._scalars


class FakeSession:
    """记录 add/flush/commit，execute 返回预设的标量列表。"""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed: int = 0
        self.committed: int = 0
        # execute(...).scalars().all() 应返回的数据（按用例设置）
        self.scalar_items: list = []
        self._next_id = 1

    def add(self, obj: object) -> None:
        self.added.append(obj)
        # 模拟 flush 为主键自增的 ORM 实体分配 id
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1

    def flush(self) -> None:
        self.flushed += 1
        # 模拟 DB server_default：为尚未赋值的时间字段盖当前时间
        now = datetime.now(UTC)
        for obj in self.added:
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = now

    def commit(self) -> None:
        self.committed += 1

    def execute(self, _stmt):
        return _FakeExecuteResult(self.scalar_items)


class FakeAppRepo:
    """内存版应用仓库替身。"""

    def __init__(self) -> None:
        self.session = FakeSession()
        # 预置应用：id -> entity
        self.apps: dict[int, OpenApiAppEntity] = {}
        # find_by_name_owner 命中的应用（None=无同名）
        self.same_name: OpenApiAppEntity | None = None
        # list_user_ids_by_perm 返回的审批人 ID 列表
        self.approver_ids: list[int] = []

    def get_by_id(self, id: int) -> OpenApiAppEntity | None:
        return self.apps.get(id)

    def get_by_app_id(self, app_id: str) -> OpenApiAppEntity | None:
        return next((e for e in self.apps.values() if e.app_id == app_id), None)

    def find_by_name_owner(self, name: str, owner_type: str, owner_id: int) -> OpenApiAppEntity | None:
        return self.same_name

    def search_by_keyword(self, *, keyword=None, owner_type=None, owner_id=None, skip=0, limit=100):
        items = list(self.apps.values())
        return items, len(items)

    def list_user_ids_by_perm(self, perm_code: str) -> list[int]:
        return self.approver_ids


class FakeRegistrationRepo:
    """内存版申请/审批仓库替身。"""

    def __init__(self) -> None:
        # app_id -> 当前 pending 申请（None 表示无 pending）
        self.pending: dict[int, OpenApiAppRegistrationEntity | None] = {}
        # app_id -> 全部申请批次（list_by_app 返回）
        self.registrations: dict[int, list[OpenApiAppRegistrationEntity]] = {}
        # app_id -> 最近一条申请（find_latest_by_app）
        self.latest: dict[int, OpenApiAppRegistrationEntity | None] = {}
        # code 已占用集合
        self.existing_codes: set[str] = set()

    def find_pending_by_app(self, app_id: int):
        return self.pending.get(app_id)

    def list_by_app(self, app_id: int):
        return self.registrations.get(app_id, [])

    def find_latest_by_app(self, app_id: int):
        return self.latest.get(app_id)

    def code_exists(self, code: str) -> bool:
        return code in self.existing_codes


# ── 实体工厂 ──────────────────────────────────────────


def _make_app(id: int = 1, **overrides) -> OpenApiAppEntity:
    """构造一个开发者名下、已启用的应用实体。"""
    now = datetime.now(UTC)
    kwargs: dict = {
        "id": id,
        "app_id": f"hj_test_{id:04d}",
        "app_key_hash": "x",
        "app_key_encrypted": "enc",
        "name": f"应用{id}",
        "description": "描述",
        "owner_type": AppOwnerType.DEVELOPER.value,
        "owner_id": 7,
        "approved": True,
        "scopes": "user:read",
        "status": AppStatus.ACTIVE.value,
        "auth_mode": "plain",
        "rate_limit_per_minute": 60,
        "app_key_viewed_at": None,
        "last_used_at": None,
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return OpenApiAppEntity(**kwargs)


def _make_registration(id: int = 1, app_id: int = 1, **overrides) -> OpenApiAppRegistrationEntity:
    now = datetime.now(UTC)
    kwargs: dict = {
        "id": id,
        "registration_code": "123456",
        "app_id": app_id,
        "registration_type": AppRegistrationType.CREATE.value,
        "name": "应用1",
        "description": "描述",
        "scopes": "user:read",
        "auth_mode": "plain",
        "apply_reason": None,
        "status": AppApprovalStatus.PENDING.value,
        "approved_by": None,
        "approval_note": None,
        "approved_at": None,
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return OpenApiAppRegistrationEntity(**kwargs)


def _make_service(repo: FakeAppRepo | None = None, reg_repo: FakeRegistrationRepo | None = None):
    repo = repo or FakeAppRepo()
    reg_repo = reg_repo or FakeRegistrationRepo()
    svc = DeveloperOpenApiAppService(repo=repo, registration_repo=reg_repo)
    return svc, repo, reg_repo


def _create_payload(**overrides) -> OpenAppCreateRequest:
    kwargs: dict = {
        "name": "新应用",
        "description": "新应用描述",
        "scopes": ["user:read"],
        "auth_mode": "plain",
    }
    kwargs.update(overrides)
    return OpenAppCreateRequest(**kwargs)


class TestQuery:
    """查询类行为。"""

    def test_list_my_apps_pagination(self) -> None:
        """分页查询返回 items/total/page/page_size。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1)
        repo.apps[2] = _make_app(2)
        svc, _, _ = _make_service(repo=repo)

        page = svc.list_my_apps(7, page=1, page_size=20)
        assert page["total"] == 2
        assert page["page"] == 1
        assert page["page_size"] == 20
        assert len(page["items"]) == 2

    def test_get_my_app_success(self) -> None:
        """获取本人应用详情成功，派生审批状态为 approved。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1)
        svc, _, _ = _make_service(repo=repo)

        resp = svc.get_my_app(1, 7)
        assert resp.id == 1
        assert resp.approval_status == AppApprovalStatus.APPROVED.value

    def test_get_my_app_not_owner_raises_not_found(self) -> None:
        """应用归属他人 → NotFoundException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, owner_id=999)
        svc, _, _ = _make_service(repo=repo)

        with pytest.raises(NotFoundException):
            svc.get_my_app(1, 7)

    def test_get_my_app_disabled_raises_conflict(self) -> None:
        """禁用中的应用禁止读取详情 → ConflictException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, status=AppStatus.DISABLED.value)
        svc, _, _ = _make_service(repo=repo)

        with pytest.raises(ConflictException, match="已被管理员禁用"):
            svc.get_my_app(1, 7)

    def test_get_public_scopes_attaches_sort_order(self) -> None:
        """scope 目录查询为每项附加 sort_order。"""
        svc, repo, _ = _make_service()
        repo.session.scalar_items = [
            SimpleNamespace(
                id=1,
                scope_code="user:read",
                scope_name="读用户",
                module="user",
                operation="read",
                description="",
                sort_order=10,
            ),
            SimpleNamespace(
                id=2,
                scope_code="order:read",
                scope_name="读订单",
                module="order",
                operation="read",
                description="",
                sort_order=5,
            ),
        ]
        scopes = svc.get_public_scopes()
        assert len(scopes) == 2
        assert scopes[0]["sort_order"] == 10
        assert scopes[0]["scope_code"] == "user:read"

    def test_list_approvals_resolves_approver_name(self) -> None:
        """审批历史组装响应，并按 approved_by 解析审批人姓名。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True)
        reg_repo = FakeRegistrationRepo()
        reg = _make_registration(1, app_id=1, approved_by=10, approval_note="同意")
        reg_repo.registrations[1] = [reg]
        svc, repo, _ = _make_service(repo=repo, reg_repo=reg_repo)
        # 审批人用户表查询结果
        repo.session.scalar_items = [SimpleNamespace(id=10, name="张管理员", username="admin10")]

        approvals = svc.list_approvals(1, 7)
        assert len(approvals) == 1
        assert approvals[0].approver_name == "张管理员"
        assert approvals[0].note == "同意"


class TestCreateApp:
    """创建申请行为。"""

    def test_create_success_notifies_approvers(self) -> None:
        """创建成功：落应用与申请批次，并给审批人写站内信。"""
        repo = FakeAppRepo()
        repo.approver_ids = [100, 101]
        reg_repo = FakeRegistrationRepo()
        svc, repo, reg_repo = _make_service(repo=repo, reg_repo=reg_repo)

        resp = svc.create_app(7, payload=_create_payload())
        assert resp.name == "新应用"
        assert resp.approved is False
        # 应用 + 申请批次两条 add
        added_types = [type(o).__name__ for o in repo.session.added]
        assert added_types.count("OpenApiAppEntity") == 1
        assert added_types.count("OpenApiAppRegistrationEntity") == 1
        # 两个审批人站内信
        msgs = [o for o in repo.session.added if isinstance(o, StationMessageEntity)]
        assert len(msgs) == 2
        assert repo.session.committed == 1

    def test_create_without_approver_skips_notice(self) -> None:
        """无审批人：仅警告不写站内信，创建照常完成。"""
        repo = FakeAppRepo()
        repo.approver_ids = []
        svc, repo, _ = _make_service(repo=repo)

        resp = svc.create_app(7, payload=_create_payload())
        assert resp.name == "新应用"
        assert not any(isinstance(o, StationMessageEntity) for o in repo.session.added)

    def test_create_duplicate_name_raises_conflict(self) -> None:
        """同名应用 → ConflictException。"""
        repo = FakeAppRepo()
        repo.same_name = _make_app(1)
        svc, _, _ = _make_service(repo=repo)

        with pytest.raises(ConflictException, match="已存在名为"):
            svc.create_app(7, payload=_create_payload())

    def test_invalid_auth_mode_raises_validation(self) -> None:
        """DB 中存在非法 auth_mode 实体时，更新触发服务层校验 → ValidationException。

        请求 schema 已用正则限制 auth_mode，故非法值只能来自存量数据；
        此时 update_app 不覆盖 auth_mode，沿用实体原值触发 _validate_auth_mode。
        """
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True, auth_mode="legacy-bad")
        svc, _, _ = _make_service(repo=repo)

        with pytest.raises(ValidationException, match="不支持的鉴权模式"):
            svc.update_app(1, 7, payload=OpenAppUpdateRequest(name="改名"))


class TestUpdateAndApply:
    """修改信息 / 申请权限行为。"""

    def test_update_app_success(self) -> None:
        """提交修改申请成功。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True)
        svc, repo, _ = _make_service(repo=repo)

        resp = svc.update_app(1, 7, payload=OpenAppUpdateRequest(name="改名后"))
        assert resp.id == 1
        # 产生一条 update 申请批次
        regs_added = [o for o in repo.session.added if isinstance(o, OpenApiAppRegistrationEntity)]
        assert len(regs_added) == 1
        assert regs_added[0].registration_type == AppRegistrationType.UPDATE.value

    def test_update_app_pending_conflict(self) -> None:
        """存在 pending 申请 → ConflictException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True)
        reg_repo = FakeRegistrationRepo()
        reg_repo.pending[1] = _make_registration(1, app_id=1)
        svc, _, _ = _make_service(repo=repo, reg_repo=reg_repo)

        with pytest.raises(ConflictException, match="待审批"):
            svc.update_app(1, 7, payload=OpenAppUpdateRequest(name="再改名"))

    def test_apply_scopes_success(self) -> None:
        """提交 scope 调整申请成功，携带申请原因。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True)
        svc, repo, _ = _make_service(repo=repo)

        payload = OpenAppScopeApplyRequest(scopes=["order:write"], reason="需要下单")
        svc.apply_scopes(1, 7, payload=payload)
        regs_added = [o for o in repo.session.added if isinstance(o, OpenApiAppRegistrationEntity)]
        assert regs_added[0].apply_reason == "需要下单"

    def test_apply_scopes_pending_conflict(self) -> None:
        """scope 申请遇 pending → ConflictException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True)
        reg_repo = FakeRegistrationRepo()
        reg_repo.pending[1] = _make_registration(1, app_id=1)
        svc, _, _ = _make_service(repo=repo, reg_repo=reg_repo)

        with pytest.raises(ConflictException):
            svc.apply_scopes(1, 7, payload=OpenAppScopeApplyRequest(scopes=["x"]))


class TestKeyManagement:
    """密钥重置 / 一次性查看。"""

    def test_rotate_key_success(self) -> None:
        """重置密钥返回新明文，并清空 viewed_at。"""
        repo = FakeAppRepo()
        app = _make_app(1, approved=True, app_key_viewed_at=datetime.now(UTC))
        repo.apps[1] = app
        svc, repo, _ = _make_service(repo=repo)

        result = svc.rotate_key(1, 7)
        assert result["app_id"] == app.app_id
        assert result["app_key"]
        assert app.app_key_viewed_at is None
        assert repo.session.committed == 1

    def test_view_secret_success(self) -> None:
        """已审批且未查看过 → 返回明文并记录 viewed_at。"""
        repo = FakeAppRepo()
        app = _make_app(1, approved=True, app_key_viewed_at=None)
        repo.apps[1] = app
        # 用真实加密：先加密一个明文，再让 view_secret 能解密
        from src.utils import security

        plain = "my-app-key-plain"
        app.app_key_encrypted = security.encrypt_text(plain)
        svc, repo, _ = _make_service(repo=repo)

        result = svc.view_secret(1, 7)
        assert result["app_key"] == plain
        assert app.app_key_viewed_at is not None

    def test_view_secret_not_approved(self) -> None:
        """未通过审批 → ConflictException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=False)
        svc, _, _ = _make_service(repo=repo)
        with pytest.raises(ConflictException, match="尚未通过创建审批"):
            svc.view_secret(1, 7)

    def test_view_secret_already_viewed(self) -> None:
        """已查看过一次 → ConflictException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True, app_key_viewed_at=datetime.now(UTC))
        svc, _, _ = _make_service(repo=repo)
        with pytest.raises(ConflictException, match="已展示过一次"):
            svc.view_secret(1, 7)

    def test_view_secret_no_ciphertext(self) -> None:
        """密文缺失 → ConflictException。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=True, app_key_encrypted=None)
        svc, _, _ = _make_service(repo=repo)
        with pytest.raises(ConflictException, match="密钥数据异常"):
            svc.view_secret(1, 7)


class TestDeleteApp:
    """删除应用行为。"""

    def test_delete_app_rejects_pending(self) -> None:
        """删除应用：软删并把 pending 申请作废。"""
        repo = FakeAppRepo()
        app = _make_app(1)
        repo.apps[1] = app
        reg_repo = FakeRegistrationRepo()
        pending = _make_registration(1, app_id=1)
        reg_repo.pending[1] = pending
        svc, repo, _ = _make_service(repo=repo, reg_repo=reg_repo)

        svc.delete_app(1, 7)
        assert app.deleted_at is not None
        assert pending.status == AppApprovalStatus.REJECTED.value
        assert "作废" in (pending.approval_note or "")

    def test_delete_app_without_pending(self) -> None:
        """无 pending 申请：仅软删应用。"""
        repo = FakeAppRepo()
        app = _make_app(1)
        repo.apps[1] = app
        svc, repo, _ = _make_service(repo=repo)

        svc.delete_app(1, 7)
        assert app.deleted_at is not None
        assert repo.session.committed == 1


class TestApprovalStatusDerivation:
    """_to_response 审批状态派生分支。"""

    def test_derived_status_rejected_when_latest_rejected(self) -> None:
        """未审批、最近一次申请被驳回 → 派生 rejected。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=False)
        reg_repo = FakeRegistrationRepo()
        reg_repo.latest[1] = _make_registration(1, app_id=1, status=AppApprovalStatus.REJECTED.value)
        svc, _, _ = _make_service(repo=repo, reg_repo=reg_repo)

        resp = svc.get_my_app(1, 7)
        assert resp.approval_status == AppApprovalStatus.REJECTED.value

    def test_derived_status_none_when_no_history(self) -> None:
        """未审批、无任何申请记录 → approval_status 为 None。"""
        repo = FakeAppRepo()
        repo.apps[1] = _make_app(1, approved=False)
        svc, _, _ = _make_service(repo=repo)

        resp = svc.get_my_app(1, 7)
        assert resp.approval_status is None
