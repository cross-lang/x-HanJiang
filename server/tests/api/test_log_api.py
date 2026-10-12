#!/usr/bin/env python3
"""管理端日志接口（src/api/admin/v1/log.py）单元测试。

直接调用 handler 函数体（@permission 仅挂载元数据，不改变函数行为），
用 FakeAuditService / FakeLoginService 隔离仓储，覆盖：
    - describe_audit_action：审计动作中文映射
    - list_audit_logs：管理员看全部 / 普通用户强制限定本人 / 操作人姓名回填
    - export_audit_logs：CSV 中文表头与动作中文描述
    - get_audit_log：存在回填操作人 / 不存在抛 404
    - list_login_logs：管理员看全部 / 普通用户仅本人
    - export_login_logs：CSV 导出
    - get_login_log：存在 / 不存在
"""

import asyncio
import json
from datetime import datetime

import pytest
from src.api.admin.v1 import log as log_api
from src.constants.permissions import PermissionAction
from src.core.exceptions import NotFoundException
from src.models.entities.audit_entity import AuditLogEntity
from src.schemas.admin.auth import CurrentUser
from src.schemas.admin.login_log import LoginLogResponse
from starlette.requests import Request


def _make_request() -> Request:
    """构造最小可用 Request（success_response 仅读取 request.state.request_id，缺省为 None）。"""
    return Request({"type": "http", "headers": [], "query_string": b"", "method": "GET"})


def _admin_user() -> CurrentUser:
    """超级管理员（permissions 含 * ）。"""
    return CurrentUser(
        id=1,
        username="admin",
        email="admin@example.com",
        name="管理员",
        role_code="superadmin",
        status="enabled",
        permissions=["*"],
    )


def _normal_user() -> CurrentUser:
    """普通用户（无 * 权限）。"""
    return CurrentUser(
        id=5,
        username="alice",
        email="alice@example.com",
        name="Alice",
        role_code="user",
        status="enabled",
        permissions=[],
    )


class FakeAuditService:
    """审计服务替身：按内存列表返回，并记录最后一次 search 参数。"""

    def __init__(self, items: list[AuditLogEntity], op_names: dict | None = None) -> None:
        self._items = items
        self._op_names = op_names or {}
        self.last_search: dict = {}

    def search(self, **kwargs):
        self.last_search = kwargs
        return {
            "items": self._items,
            "total": len(self._items),
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 20),
        }

    def get_by_id(self, log_id: int):
        return next((i for i in self._items if i.id == log_id), None)

    def get_operator_names(self, user_ids):
        return {uid: self._op_names[uid] for uid in user_ids if uid in self._op_names}


class FakeLoginService:
    """登录日志服务替身：按内存列表返回，并记录最后一次 search 参数。"""

    def __init__(self, items: list[LoginLogResponse], detail: LoginLogResponse | None = None) -> None:
        self._items = items
        self._detail = detail
        self.last_search: dict = {}

    def search(self, **kwargs):
        self.last_search = kwargs
        return {
            "items": self._items,
            "total": len(self._items),
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 20),
        }

    def get_detail(self, log_id: int):
        return self._detail


def _audit_entity(aid: int, operator_id: int | None = 7, action: str = "create") -> AuditLogEntity:
    return AuditLogEntity(
        id=aid,
        entity_type="user",
        entity_id="1",
        action=action,
        operator_id=operator_id,
        ip_address="1.1.1.1",
        remarks="创建用户",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )


def _body(response) -> dict:
    """解析 JSONResponse 字节体为 dict。"""
    return json.loads(response.body)


def _stream_bytes(response) -> bytes:
    """消费 StreamingResponse 的异步字节流为完整 bytes。"""

    async def _collect() -> bytes:
        return b"".join([chunk async for chunk in response.body_iterator])

    return asyncio.run(_collect())


class TestDescribeAuditAction:
    """审计动作中文展示映射。"""

    def test_audit_action_enum(self):
        """AuditAction 独有动作（login）返回其中文描述。"""
        assert log_api.describe_audit_action("login") == "登录"

    def test_permission_action_enum(self):
        """PermissionAction 动作回退到权限动作中文描述。"""
        assert log_api.describe_audit_action(PermissionAction.UPLOAD.mark) == PermissionAction.UPLOAD.desc

    def test_extra_navigate(self):
        """AI 助手跳转动作兜底映射。"""
        assert log_api.describe_audit_action("navigate") == "跳转"

    def test_unknown_returns_raw(self):
        """未知动作原样返回。"""
        assert log_api.describe_audit_action("some_unknown") == "some_unknown"


class TestListAuditLogs:
    """审计日志列表接口。"""

    def test_admin_sees_all(self):
        """管理员不强制 operator_id，按传入条件查询。"""
        svc = FakeAuditService([_audit_entity(1)])
        log_api.list_audit_logs(
            _make_request(),
            entity_type="user",
            action=None,
            operator_id=None,
            start_time=None,
            end_time=None,
            keyword=None,
            page=1,
            page_size=20,
            audit_service=svc,
            current_user=_admin_user(),
        )
        # 管理员：保留传入的 operator_id（None）
        assert svc.last_search["operator_id"] is None

    def test_normal_user_limited_to_self(self):
        """普通用户强制 operator_id = 当前用户 id。"""
        svc = FakeAuditService([_audit_entity(1, operator_id=5)])
        log_api.list_audit_logs(
            _make_request(),
            entity_type=None,
            action=None,
            operator_id=999,  # 传入会被覆盖
            start_time=None,
            end_time=None,
            keyword=None,
            page=1,
            page_size=20,
            audit_service=svc,
            current_user=_normal_user(),
        )
        assert svc.last_search["operator_id"] == 5

    def test_operator_name_filled(self):
        """操作人用户名/姓名回填到每条记录。"""
        svc = FakeAuditService(
            [_audit_entity(1, operator_id=7)],
            op_names={7: {"username": "zhangsan", "name": "张三"}},
        )
        resp = log_api.list_audit_logs(
            _make_request(),
            entity_type=None,
            action=None,
            operator_id=None,
            start_time=None,
            end_time=None,
            keyword=None,
            page=1,
            page_size=20,
            audit_service=svc,
            current_user=_admin_user(),
        )
        item = _body(resp)["data"]["items"][0]
        assert item["operator_username"] == "zhangsan"
        assert item["operator_real_name"] == "张三"


class TestExportAuditLogs:
    """审计日志 CSV 导出。"""

    def test_export_csv_content(self):
        svc = FakeAuditService(
            [_audit_entity(1, action="login")],
            op_names={7: {"username": "zhangsan", "name": "张三"}},
        )
        resp = log_api.export_audit_logs(
            entity_type=None,
            action=None,
            operator_id=None,
            start_time=None,
            end_time=None,
            audit_service=svc,
        )
        content = _stream_bytes(resp).decode("utf-8-sig")
        # 中文表头 + 动作被翻译为中文
        assert "实体类型" in content
        assert "登录" in content


class TestGetAuditLog:
    """审计日志详情。"""

    def test_found_with_operator(self):
        svc = FakeAuditService(
            [_audit_entity(1, operator_id=7)],
            op_names={7: {"username": "zhangsan", "name": "张三"}},
        )
        resp = log_api.get_audit_log(1, _make_request(), audit_service=svc, _=_admin_user())
        data = _body(resp)["data"]
        assert data["operator_username"] == "zhangsan"

    def test_not_found(self):
        svc = FakeAuditService([])
        with pytest.raises(NotFoundException):
            log_api.get_audit_log(999, _make_request(), audit_service=svc, _=_admin_user())


class TestListLoginLogs:
    """登录日志列表接口。"""

    def test_admin_sees_all(self):
        svc = FakeLoginService([])
        log_api.list_login_logs(
            _make_request(),
            user_id=None,
            status=None,
            login_type=None,
            start_time=None,
            end_time=None,
            keyword=None,
            page=1,
            page_size=20,
            login_service=svc,
            current_user=_admin_user(),
        )
        assert svc.last_search["user_id"] is None

    def test_normal_user_limited_to_self(self):
        svc = FakeLoginService([])
        log_api.list_login_logs(
            _make_request(),
            user_id=999,
            status=None,
            login_type=None,
            start_time=None,
            end_time=None,
            keyword=None,
            page=1,
            page_size=20,
            login_service=svc,
            current_user=_normal_user(),
        )
        assert svc.last_search["user_id"] == 5


class TestExportLoginLogs:
    """登录日志 CSV 导出。"""

    def test_export_csv_content(self):
        item = LoginLogResponse(
            id=1,
            user_id=7,
            username="zhangsan",
            name="张三",
            login_type="password",
            login_type_label="密码",
            ip_address="2.2.2.2",
            status="success",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        svc = FakeLoginService([item])
        resp = log_api.export_login_logs(
            _make_request(),
            status=None,
            login_type=None,
            start_time=None,
            end_time=None,
            login_service=svc,
            current_user=_admin_user(),
        )
        content = _stream_bytes(resp).decode("utf-8-sig")
        assert "用户名" in content
        assert "zhangsan" in content


class TestGetLoginLog:
    """登录日志详情。"""

    def test_found(self):
        detail = LoginLogResponse(
            id=1,
            user_id=7,
            username="zhangsan",
            name="张三",
            login_type="password",
            ip_address="2.2.2.2",
            status="success",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        svc = FakeLoginService([], detail=detail)
        resp = log_api.get_login_log(1, _make_request(), login_service=svc, _=_admin_user())
        data = _body(resp)["data"]
        assert data["username"] == "zhangsan"

    def test_not_found(self):
        svc = FakeLoginService([], detail=None)
        with pytest.raises(NotFoundException):
            log_api.get_login_log(999, _make_request(), login_service=svc, _=_admin_user())
