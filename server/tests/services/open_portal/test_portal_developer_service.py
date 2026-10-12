#!/usr/bin/env python3
"""开放门户开发者资料/认证服务测试（src/services/open_portal/developer_service.py）。

DeveloperService 管理开发者个人中心：
    - 查询资料：存在 / 不存在
    - 更新资料：姓名/手机号部分更新（exclude_unset）
    - 提交认证：个人认证 / 企业认证（企业名必填校验）
外部仓库以内存 Fake 替身，不连真实 DB。
"""

from datetime import UTC, datetime

import pytest
from src.core.exceptions import ValidationException
from src.models.entities.developer_entity import DeveloperEntity
from src.schemas.open_portal.developer import (
    DeveloperCertificationRequest,
    DeveloperProfileUpdateRequest,
)
from src.services.open_portal.developer_service import DeveloperService


class FakeDeveloperRepository:
    """内存版开发者仓库替身。"""

    def __init__(self, dev: DeveloperEntity | None = None) -> None:
        self._dev = dev
        self.committed: int = 0

    def get_by_id(self, id: int) -> DeveloperEntity | None:
        return self._dev

    def commit(self) -> None:
        self.committed += 1


def _make_dev(id: int = 7, **overrides) -> DeveloperEntity:
    now = datetime.now(UTC)
    kwargs: dict = {
        "id": id,
        "username": f"dev{id}",
        "email": f"dev{id}@example.com",
        "password_hash": "x",
        "name": "原姓名",
        "phone": "13800000000",
        "certification_type": None,
        "certification_status": "none",
        "company_name": None,
        "credential_no": None,
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return DeveloperEntity(**kwargs)


def _make_service(dev: DeveloperEntity | None = None):
    repo = FakeDeveloperRepository(dev=dev)
    return DeveloperService(repository=repo), repo


class TestProfile:
    """资料查询与更新。"""

    def test_get_profile_success(self) -> None:
        """查询开发者资料成功。"""
        svc, _ = _make_service(_make_dev())
        resp = svc.get_profile(7)
        assert resp.id == 7
        assert resp.username == "dev7"
        assert resp.certification_status == "none"

    def test_get_profile_not_found_raises(self) -> None:
        """开发者不存在 → ValidationException。"""
        svc, _ = _make_service(None)
        with pytest.raises(ValidationException, match="开发者不存在"):
            svc.get_profile(999)

    def test_update_profile_full(self) -> None:
        """更新姓名与手机号成功。"""
        dev = _make_dev()
        svc, repo = _make_service(dev)

        resp = svc.update_profile(
            7,
            DeveloperProfileUpdateRequest(name="新姓名", phone="13900000000"),
        )
        assert resp.name == "新姓名"
        assert resp.phone == "13900000000"
        assert repo.committed == 1

    def test_update_profile_partial_keeps_other(self) -> None:
        """部分更新：仅改姓名时手机号保持不变（exclude_unset）。"""
        dev = _make_dev(phone="13111111111")
        svc, _ = _make_service(dev)

        resp = svc.update_profile(7, DeveloperProfileUpdateRequest(name="只改名"))
        assert resp.name == "只改名"
        assert resp.phone == "13111111111"


class TestCertification:
    """开发者认证申请。"""

    def test_apply_personal_certification(self) -> None:
        """个人认证：状态置 pending，企业字段留空。"""
        dev = _make_dev()
        svc, repo = _make_service(dev)

        resp = svc.apply_certification(
            7,
            DeveloperCertificationRequest(certification_type="personal"),
        )
        assert resp.certification_type == "personal"
        assert resp.certification_status == "pending"
        assert resp.company_name is None
        assert repo.committed == 1

    def test_apply_enterprise_certification_with_name(self) -> None:
        """企业认证且填写企业名 → 记录企业名与证件号。"""
        dev = _make_dev()
        svc, _ = _make_service(dev)

        resp = svc.apply_certification(
            7,
            DeveloperCertificationRequest(
                certification_type="enterprise",
                company_name="  汉江科技有限公司  ",
                credential_no="91420000XXXX",
            ),
        )
        assert resp.certification_type == "enterprise"
        # 企业名去空白后落库
        assert resp.company_name == "汉江科技有限公司"

    def test_apply_enterprise_without_name_raises(self) -> None:
        """企业认证未填企业名 → ValidationException。"""
        dev = _make_dev()
        svc, repo = _make_service(dev)

        with pytest.raises(ValidationException, match="企业认证必须填写企业名称"):
            svc.apply_certification(7, DeveloperCertificationRequest(certification_type="enterprise"))
        assert repo.committed == 0

    def test_apply_certification_not_found_raises(self) -> None:
        """对不存在的开发者提交认证 → ValidationException。"""
        svc, _ = _make_service(None)
        with pytest.raises(ValidationException, match="开发者不存在"):
            svc.apply_certification(999, DeveloperCertificationRequest(certification_type="personal"))
