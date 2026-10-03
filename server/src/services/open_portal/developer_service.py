#!/usr/bin/env python3
"""开放平台开发者资料与认证业务逻辑。"""

from __future__ import annotations

from src.constants.enums import CertificationStatus, CertificationType
from src.core.exceptions import ValidationException
from src.models.entities.developer_entity import DeveloperEntity
from src.repositories.developer_repository import DeveloperRepository
from src.schemas.open_portal.auth import (
    DeveloperCertificationRequest,
    DeveloperProfileResponse,
    DeveloperProfileUpdateRequest,
)


class DeveloperService:
    """开发者资料管理。"""

    def __init__(self, repository: DeveloperRepository) -> None:
        self._repository = repository

    def get_profile(self, developer_id: int) -> DeveloperProfileResponse:
        """查询开发者资料（个人中心）。"""
        dev = self._require_developer(developer_id)
        return self._to_profile(dev)

    def update_profile(
        self,
        developer_id: int,
        patch: DeveloperProfileUpdateRequest,
    ) -> DeveloperProfileResponse:
        """更新开发者基本信息（姓名/手机号）。"""
        dev = self._require_developer(developer_id)
        data = patch.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            dev.name = data["name"]
        if "phone" in data and data["phone"] is not None:
            dev.phone = data["phone"]
        self._repository.commit()
        return self._to_profile(dev)

    def apply_certification(
        self,
        developer_id: int,
        request: DeveloperCertificationRequest,
    ) -> DeveloperProfileResponse:
        """提交开发者认证申请（预留流程：状态置 pending，等待管理员审批）。

        Args:
            developer_id: 开发者 ID
            request: 认证申请（个人/企业）

        Returns:
            DeveloperProfileResponse: 更新后的资料

        Raises:
            ValidationException: 企业认证未填企业名称
        """
        dev = self._require_developer(developer_id)
        is_enterprise = request.certification_type == CertificationType.ENTERPRISE.value
        if is_enterprise and not (request.company_name or "").strip():
            raise ValidationException(message="企业认证必须填写企业名称")
        dev.certification_type = request.certification_type
        dev.certification_status = CertificationStatus.PENDING.value
        dev.company_name = (request.company_name or "").strip() or None
        dev.credential_no = (request.credential_no or "").strip() or None
        self._repository.commit()
        return self._to_profile(dev)

    # ── 内部工具 ────────────────────────────────────────

    def _require_developer(self, developer_id: int) -> DeveloperEntity:
        """按 ID 取开发者，不存在抛校验异常。"""
        dev = self._repository.get_by_id(developer_id)
        if dev is None:
            raise ValidationException(message="开发者不存在")
        return dev

    def _to_profile(self, e: DeveloperEntity) -> DeveloperProfileResponse:
        return DeveloperProfileResponse(
            id=e.id,
            username=e.username,
            email=e.email,
            name=e.name,
            phone=e.phone,
            certification_type=e.certification_type,
            certification_status=e.certification_status,
            company_name=e.company_name,
            created_at=e.created_at,
        )
