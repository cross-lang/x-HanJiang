#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据格式转换模块

提供 XML/JSON/YAML 之间的常用转换能力，并包含对象/字典互转等辅助方法。
"""

import json
import xmltodict

from typing import Any

import yaml


class ConvertTool:

    @classmethod
    def xml_file_to_json_file(cls, xml_file: str, json_file: str) -> dict[str, Any] | None:
        """ 将xml格式文件转为json格式文件（python对象） """
        with open(xml_file, mode="r", encoding="utf-8") as f, open(json_file, "w", encoding="utf-8") as f1:
            order_dict = xmltodict.parse(f.read(), encoding="utf-8")
            common_dict: dict[str, Any] = json.loads(json.dumps(order_dict, ensure_ascii=False))
            f1.write(json.dumps(common_dict, ensure_ascii=False))
            return common_dict

    @classmethod
    def xml_data_to_json_data(cls, xml_data: str) -> dict[str, Any]:
        """ 将xml格式数据转为json格式数据 """
        order_dict = xmltodict.parse(xml_data, encoding="utf-8")
        return json.loads(json.dumps(order_dict, ensure_ascii=False))

    @classmethod
    def yaml_dump(cls, obj: Any) -> str | None:
        """ 将json格式数据（python对象）转换为yaml格式数据 """
        try:
            return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)
        except Exception:
            return None

    @classmethod
    def yaml_load(cls, stream: str) -> Any | None:
        """ 将yaml格式数据转换为json格式数据（python对象） """
        try:
            return yaml.safe_load(stream)
        except Exception:
            return None

    @classmethod
    def float_to_int(cls, value: float | int | str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(float(value))

    @classmethod
    def dict_to_obj(cls, raw_dict: dict[str, Any]) -> Any:
        """ 字典转对象 """
        class Dict(dict):
            __setattr__ = dict.__setitem__
            __getattr__ = dict.__getitem__

        if not isinstance(raw_dict, dict):
            return raw_dict

        dt_obj = Dict()
        for k, v in raw_dict.items():
            dt_obj[k] = cls.dict_to_obj(v)
        return dt_obj

    @classmethod
    def obj_to_dict(cls, dict_obj: Any) -> dict[str, Any]:
        """ 对象转字典
            方法待确认
        """
        return dict_obj.__dict__


if __name__ == '__main__':
    dt_obj = ConvertTool.dict_to_obj({"name": "xxx", "age": 18})
    print(dir(dt_obj))
    print(type(dt_obj))
    print(dt_obj.name)
    print(dt_obj.age)
