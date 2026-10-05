#!/usr/bin/env python3
"""开放平台通用工具——应用身份与 scope 目录的公共协议函数。

从 services/admin/openapi_app_service.py 抽出的公共片段：
- generate_app_id / parse_scopes：管理员侧与开发者域共用（开发者域不得反向依赖管理端服务）；
- build_scope_dict_list：scope 目录实体 → 前端展示 dict（模块中文名映射）。
管理端服务保留同名 re-export，旧引用无需改动。
"""

import secrets
from typing import Any

from src.constants.scopes import OpenApiScopeCode, OpenApiScopeModule
from src.core.exceptions import ValidationException


def generate_app_id() -> str:
    """生成对外 AppId。
    前缀 = 项目缩写 hj + 环境标识：
        - 生产环境：hj_live_xxxxxxxx
        - 其他环境：hj_test_xxxxxxxx
    主体 16 字节随机 → 32 hex 字符，约 128bit 熵，抗枚举。
    """
    return f"hj_{secrets.token_hex(10)}"


def parse_scopes(scopes: str | None) -> list[str]:
    """库中逗号分隔的 scopes 字段 → list[str]，去空。"""
    if not scopes:
        return []
    return [s.strip() for s in scopes.split(",") if s.strip()]


def validate_scopes(scopes: list[str]) -> None:
    """校验 scope 列表必须全部在合法目录（OpenApiScopeCode 枚举）内。

    写入 openapi_apps.scopes 前必须调用：scope 为有限固定目录，
    不在目录内的值（拼写错误、已下线 scope）永远无法通过网关鉴权，
    属于必须拒绝的脏数据。重复项自动去重，不影响校验结果。

    Args:
        scopes: 待校验的 scope 编码列表

    Raises:
        ValidationException: 存在不在 OpenApiScopeCode 目录内的 scope 时抛出，
            错误信息列出全部非法值，便于调用方修正
    """
    if not scopes:
        return
    valid_marks = {scope.mark for scope in OpenApiScopeCode}
    invalid = sorted({s for s in scopes if s not in valid_marks})
    if invalid:
        raise ValidationException(
            message=f"存在非法的权限范围: {', '.join(invalid)}",
            details={"invalid_scopes": invalid, "valid_scopes": sorted(valid_marks)},
        )


def build_scope_dict_list(entities: list[Any]) -> list[dict[str, Any]]:
    """scope 元数据实体 → 前端目录 dict（含模块中文名映射）。

    Args:
        entities: OpenApiScopeEntity 列表（调用方负责排序与未废弃过滤）

    Returns:
        list[dict[str, Any]]: [{id, scope_code, scope_name, module, module_label, operation, description}]
    """
    result: list[dict[str, Any]] = []
    for e in entities:
        module_label = next(
            (m.desc for m in OpenApiScopeModule if m.mark == e.module),
            e.module,
        )
        result.append(
            {
                "id": e.id,
                "scope_code": e.scope_code,
                "scope_name": e.scope_name,
                "module": e.module,
                "module_label": module_label,
                "operation": e.operation,
                "description": e.description,
            }
        )
    return result


__all__ = ["generate_app_id", "parse_scopes", "validate_scopes", "build_scope_dict_list"]
