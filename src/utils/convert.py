#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据格式转换模块

提供 XML/JSON/YAML 之间的常用转换能力，并包含对象/字典互转等辅助方法。
此外还提供通用的字符串→基本类型转换函数（to_bool / to_int / to_float）。
"""

import json
import xmltodict

from typing import Any

import yaml


# ============================================================
# 通用字符串 → 基本类型转换（供 config / env 解析等场景复用）
# ============================================================

def to_bool(value: str | None) -> bool:
    """将字符串转换为布尔值。

    仅当值（忽略大小写）为 ``"true"`` 时返回 ``True``，其余一律返回 ``False``。
    """
    return value.lower() == "true" if value else False


def to_int(value: str | None, default: int = 0) -> int:
    """将字符串转换为整数，无法转换时返回 *default*。"""
    return int(value) if value else default


def to_float(value: str | None, default: float = 0.0) -> float:
    """将字符串转换为浮点数，无法转换时返回 *default*。"""
    return float(value) if value else default


def xml_file_to_json_file(xml_file: str, json_file: str) -> dict[str, Any] | None:
    """将 xml 格式文件转为 json 格式文件（python 对象）。"""
    with open(xml_file, mode="r", encoding="utf-8") as f, open(json_file, "w", encoding="utf-8") as f1:
        order_dict = xmltodict.parse(f.read(), encoding="utf-8")
        common_dict: dict[str, Any] = json.loads(json.dumps(order_dict, ensure_ascii=False))
        f1.write(json.dumps(common_dict, ensure_ascii=False))
        return common_dict


def xml_data_to_json_data(xml_data: str) -> dict[str, Any]:
    """将 xml 格式数据转为 json 格式数据。"""
    order_dict = xmltodict.parse(xml_data, encoding="utf-8")
    return json.loads(json.dumps(order_dict, ensure_ascii=False))


def yaml_dump(obj: Any) -> str | None:
    """将 json 格式数据（python 对象）转换为 yaml 格式数据。"""
    try:
        return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)
    except Exception:
        return None


def yaml_load(stream: str) -> Any | None:
    """将 yaml 格式数据转换为 json 格式数据（python 对象）。"""
    try:
        return yaml.safe_load(stream)
    except Exception:
        return None


def float_to_int(value: float | int | str) -> int:
    """将浮点数/字符串安全转换为整数。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(float(value))


def dict_to_obj(raw_dict: dict[str, Any]) -> Any:
    """字典转对象（递归，支持嵌套）。"""
    class Dict(dict):
        __setattr__ = dict.__setitem__
        __getattr__ = dict.__getitem__

    if not isinstance(raw_dict, dict):
        return raw_dict

    dt_obj = Dict()
    for k, v in raw_dict.items():
        dt_obj[k] = dict_to_obj(v)
    return dt_obj


def obj_to_dict(dict_obj: Any) -> dict[str, Any]:
    """对象转字典。"""
    return dict_obj.__dict__


if __name__ == '__main__':
    dt_obj = dict_to_obj({"name": "xxx", "age": 18})
    print(dir(dt_obj))
    print(type(dt_obj))
    print(dt_obj.name)
    print(dt_obj.age)
