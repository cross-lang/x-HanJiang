#!/usr/bin/env python3
"""管理端权限服务（PermissionService）单元测试。

覆盖目标模块 src/services/admin/permission_service.py：
    - 模块/操作枚举查询、权限分页搜索
    - 角色权限详情查询（角色不存在 → 404）
    - has_permission 各短路分支（缓存命中 / 超管 / 无角色 / 无权限 / 命中 / 未命中）
    - 绑定 / 解绑权限（角色不存在 / 系统内置角色禁改 / 权限不存在 / 成功）

外部依赖：Redis 用内存 Fake，审计日志由 conftest 自动降级为 no-op，不连库、不触网。
"""

from types import SimpleNamespace

import pytest
from src.core.exceptions import ConflictException, NotFoundException
from src.models.entities.user_entity import PermissionEntity
from src.services.admin.permission_service import PermissionService


class FakeCacheProvider:
    """内存版缓存提供者替身。"""

    def __init__(self) -> None:
        self.store: dict[str, object] = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, ttl: int = 300) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


class FakePermissionRepository:
    """权限仓库替身。"""

    session = None

    def __init__(self) -> None:
        self.perms: dict[int, PermissionEntity] = {}
        self.search_result: tuple[list[PermissionEntity], int] = ([], 0)
        self.exists_result = False
        self.committed = 0

    def get_all_modules(self) -> list[str]:
        return sorted({p.module for p in self.perms.values()})

    def get_all_operations(self) -> list[str]:
        return sorted({p.operation for p in self.perms.values()})

    def search(self, **kwargs):
        return self.search_result

    def get_by_id(self, id: int) -> PermissionEntity | None:
        return self.perms.get(id)

    def exists_permission_in(self, permission_ids: list[int], perm_code: str) -> bool:
        return self.exists_result

    def commit(self) -> None:
        self.committed += 1


class FakeRolePermissionRepository:
    """角色权限关联仓库替身。"""

    session = None

    def __init__(self) -> None:
        self.perms_by_role: dict[int, list[PermissionEntity]] = {}
        self.perm_ids_by_role: dict[int, list[int]] = {}
        self.added: list[tuple[int, int]] = []
        self.remove_result = True

    def get_permissions_by_role(self, role_id: int) -> list[PermissionEntity]:
        return list(self.perms_by_role.get(role_id, []))

    def get_permission_ids_by_role(self, role_id: int) -> list[int]:
        return list(self.perm_ids_by_role.get(role_id, []))

    def add_permission(self, role_id: int, permission_id: int) -> None:
        self.added.append((role_id, permission_id))

    def remove_permission(self, role_id: int, permission_id: int) -> bool:
        return self.remove_result


class FakeRoleRepository:
    """角色仓库替身。"""

    session = None

    def __init__(self) -> None:
        self.roles: dict[int, SimpleNamespace] = {}
        self.roles_by_user: dict[int, list[SimpleNamespace]] = {}

    def get_by_id(self, id: int) -> SimpleNamespace | None:
        return self.roles.get(id)

    def get_by_user_id(self, user_id: int) -> list[SimpleNamespace]:
        return list(self.roles_by_user.get(user_id, []))


class FakeUserRepository:
    """用户仓库替身：get_by_role_id 返回用户列表（用于权限变更通知）。"""

    session = None

    def __init__(self) -> None:
        self.users_by_role: dict[int, list[SimpleNamespace]] = {}

    def get_by_role_id(self, role_id: int) -> list[SimpleNamespace]:
        return list(self.users_by_role.get(role_id, []))


def _make_perm(perm_id: int = 1, code: str = "user:view") -> PermissionEntity:
    return PermissionEntity(
        id=perm_id,
        perm_code=code,
        perm_name="查看用户",
        module="user",
        operation="view",
        description=None,
        sort_order=1,
        is_deprecated=False,
    )


def _make_role(role_id: int = 10, role_type: str = "custom", role_code: str = "admin") -> SimpleNamespace:
    return SimpleNamespace(id=role_id, role_name="角色", role_code=role_code, role_type=role_type)


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch) -> FakeCacheProvider:
    fake = FakeCacheProvider()
    monkeypatch.setattr("src.infras.cache.get_cached_cache_provider", lambda: fake)
    return fake


@pytest.fixture
def repos() -> dict:
    return {
        "permission_repo": FakePermissionRepository(),
        "rp_repo": FakeRolePermissionRepository(),
        "role_repo": FakeRoleRepository(),
        "user_repo": FakeUserRepository(),
    }


@pytest.fixture
def svc(repos: dict) -> PermissionService:
    return PermissionService(
        permission_repository=repos["permission_repo"],
        role_permission_repository=repos["rp_repo"],
        role_repository=repos["role_repo"],
        user_repository=repos["user_repo"],
    )


class TestQueries:
    """模块/操作枚举与分页搜索。"""

    def test_get_all_modules(self, svc: PermissionService, repos: dict) -> None:
        repos["permission_repo"].perms[1] = _make_perm(1, "user:view")
        repos["permission_repo"].perms[2] = _make_perm(2, "role:view")
        repos["permission_repo"].perms[2].module = "role"
        assert svc.get_all_modules() == ["role", "user"]

    def test_get_all_operations(self, svc: PermissionService, repos: dict) -> None:
        repos["permission_repo"].perms[1] = _make_perm(1, "user:view")
        repos["permission_repo"].perms[2] = _make_perm(2, "user:create")
        repos["permission_repo"].perms[2].operation = "create"
        assert svc.get_all_operations() == ["create", "view"]

    def test_search_paginates(self, svc: PermissionService, repos: dict) -> None:
        repos["permission_repo"].search_result = ([_make_perm(1)], 1)
        result = svc.search(keyword="user", page=1, page_size=20)
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["items"][0].perm_code == "user:view"
        # module_label/operation_label 经枚举翻译
        assert result["items"][0].module_label == "用户管理"


class TestGetRolePermissions:
    """角色权限详情查询。"""

    def test_role_not_found(self, svc: PermissionService) -> None:
        with pytest.raises(NotFoundException):
            svc.get_role_permissions(999)

    def test_returns_permissions(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10)
        repos["rp_repo"].perms_by_role[10] = [_make_perm(1, "user:view")]
        result = svc.get_role_permissions(10)
        assert len(result) == 1
        assert result[0].role_id == 10
        assert result[0].permission.perm_code == "user:view"


class TestHasPermission:
    """权限判断（含缓存与各短路分支）。"""

    def test_cache_hit_returns_immediately(self, svc: PermissionService, repos: dict, cache: FakeCacheProvider) -> None:
        cache.store["perm:1:user:view"] = True
        assert svc.has_permission(1, "user:view") is True

    def test_superadmin_shortcircuit(self, svc: PermissionService, repos: dict, cache: FakeCacheProvider) -> None:
        repos["role_repo"].roles_by_user[1] = [SimpleNamespace(id=10, role_code="superadmin")]
        assert svc.has_permission(1, "anything") is True
        assert cache.store["perm:1:anything"] is True

    def test_no_roles(self, svc: PermissionService, repos: dict, cache: FakeCacheProvider) -> None:
        assert svc.has_permission(1, "user:view") is False

    def test_role_has_no_permission_ids(self, svc: PermissionService, repos: dict, cache: FakeCacheProvider) -> None:
        repos["role_repo"].roles_by_user[1] = [SimpleNamespace(id=10, role_code="admin")]
        repos["rp_repo"].perm_ids_by_role[10] = []
        assert svc.has_permission(1, "user:view") is False

    def test_permission_allowed(self, svc: PermissionService, repos: dict, cache: FakeCacheProvider) -> None:
        repos["role_repo"].roles_by_user[1] = [SimpleNamespace(id=10, role_code="admin")]
        repos["rp_repo"].perm_ids_by_role[10] = [1, 2]
        repos["permission_repo"].exists_result = True
        assert svc.has_permission(1, "user:view") is True
        assert cache.store["perm:1:user:view"] is True

    def test_permission_denied(self, svc: PermissionService, repos: dict, cache: FakeCacheProvider) -> None:
        repos["role_repo"].roles_by_user[1] = [SimpleNamespace(id=10, role_code="admin")]
        repos["rp_repo"].perm_ids_by_role[10] = [1, 2]
        repos["permission_repo"].exists_result = False
        assert svc.has_permission(1, "user:delete") is False


class TestBindUnbind:
    """绑定 / 解绑权限。"""

    def test_bind_role_not_found(self, svc: PermissionService) -> None:
        with pytest.raises(NotFoundException):
            svc.bind_permission(999, 1)

    def test_bind_system_role_rejected(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10, role_type="system")
        with pytest.raises(ConflictException):
            svc.bind_permission(10, 1)

    def test_bind_permission_not_found(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10)
        with pytest.raises(NotFoundException):
            svc.bind_permission(10, 999)

    def test_bind_success(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10)
        repos["permission_repo"].perms[1] = _make_perm(1)
        result = svc.bind_permission(10, 1, operator={"operator_id": 1})
        assert result.role_id == 10
        assert result.permission.perm_code == "user:view"
        assert repos["rp_repo"].added == [(10, 1)]
        assert repos["permission_repo"].committed == 1

    def test_unbind_role_not_found(self, svc: PermissionService) -> None:
        with pytest.raises(NotFoundException):
            svc.unbind_permission(999, 1)

    def test_unbind_system_role_rejected(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10, role_type="system")
        with pytest.raises(ConflictException):
            svc.unbind_permission(10, 1)

    def test_unbind_not_bound_returns_false(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10)
        repos["rp_repo"].remove_result = False
        assert svc.unbind_permission(10, 1) is False

    def test_unbind_success(self, svc: PermissionService, repos: dict) -> None:
        repos["role_repo"].roles[10] = _make_role(10)
        repos["permission_repo"].perms[1] = _make_perm(1)
        repos["rp_repo"].remove_result = True
        assert svc.unbind_permission(10, 1, operator={"operator_id": 1}) is True
        assert repos["permission_repo"].committed == 1
