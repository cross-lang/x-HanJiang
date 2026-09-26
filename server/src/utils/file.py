#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件工具模块

提供文件大小对比、生成副本、目录内搜索、JSON/YAML 读取，以及文件 MD5/SHA1/SHA256 等哈希计算能力。
"""

import os
import json
import yaml
import hashlib
from typing import Optional, Any


def compare_file_size(file_a: str, file_b: str) -> int:
    """比较文件大小。返回 1 / 0 / -1。"""
    if not file_a:
        raise ValueError("file_a不能为空")
    if not file_b:
        raise ValueError("file_b不能为空")

    file_a_size: int = os.path.getsize(file_a)
    file_b_size: int = os.path.getsize(file_b)

    if file_a_size > file_b_size:
        return 1
    if file_a_size == file_b_size:
        return 0
    else:
        return -1


def create_replica_file(file_path: str) -> Optional[str]:
    """创建文件的副本。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"源文件路径不存在: {file_path}")

    parent_path, file_name = os.path.split(file_path)
    file_name_prefix, file_name_suffix = os.path.splitext(file_name)

    replica_file_name: str = file_name_prefix
    replica_file_name += ' - 副本'
    replica_file_name += file_name_suffix
    replica_file_path: str = os.path.join(parent_path, replica_file_name)

    if os.path.exists(replica_file_path) and compare_file_size(file_path, replica_file_path) == 0:
        raise FileExistsError(f"副本文件已存在: {replica_file_path}")

    with open(file_path, encoding='utf8') as file:
        with open(replica_file_path, 'w', encoding='utf8') as f:
            for row_data in file:
                f.write(row_data)

    return replica_file_path


def get_file_size(file_path: str, unit: Optional[str] = None) -> int | float:
    """获取文件大小，可指定单位（b/kb/mb/gb/tb/pb/eb/zb/yb）。"""
    size_in_bytes: int = os.path.getsize(file_path)

    unit = unit or "b"
    if unit == "b":
        return size_in_bytes
    elif unit == "kb":
        return size_in_bytes / 1024
    elif unit == "mb":
        return size_in_bytes / 1024 / 1024
    elif unit == "gb":
        return size_in_bytes / 1024 / 1024 / 1024
    elif unit == "tb":
        return size_in_bytes / 1024 / 1024 / 1024 / 1024
    elif unit == "pb":
        return size_in_bytes / 1024 / 1024 / 1024 / 1024 / 1024
    elif unit == "eb":
        return size_in_bytes / 1024 / 1024 / 1024 / 1024 / 1024 / 1024
    elif unit == "zb":
        return size_in_bytes / 1024 / 1024 / 1024 / 1024 / 1024 / 1024 / 1024
    elif unit == "yb":
        return size_in_bytes / 1024 / 1024 / 1024 / 1024 / 1024 / 1024 / 1024 / 1024
    else:
        raise ValueError("Unit value error")


def search_file_in_dir(file_name: str, directory: str) -> Optional[str]:
    """在目录中递归搜索指定文件名。"""
    for root, _, files in os.walk(directory):
        for file in files:
            if file == file_name:
                return os.path.join(root, file)
    return None


def read_json_file(file_path: str) -> dict[str, Any]:
    """读取 JSON 文件并返回字典。"""
    if not file_path:
        raise ValueError("file_path不能为空")

    with open(file_path, encoding="utf-8") as f:
        return json.loads(f.read())


def read_yaml_file(file_path: str) -> Optional[Any]:
    """读取 YAML 文件并返回对象。"""
    if not file_path:
        raise ValueError("file_path不能为空")

    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            return yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error reading YAML file {file_path}: {e}") from e


def calculate_md5(file_path: str, buffer_size: int = 8192) -> str:
    """计算文件的 MD5 哈希值。"""
    md5_hash = hashlib.md5()

    with open(file_path, 'rb') as file:
        while chunk := file.read(buffer_size):
            md5_hash.update(chunk)

    return md5_hash.hexdigest()


def calculate_sha1(file_path: str, buffer_size: int = 8192) -> str:
    """计算文件的 SHA1 哈希值。"""
    sha1_hash = hashlib.sha1()

    with open(file_path, 'rb') as file:
        while chunk := file.read(buffer_size):
            sha1_hash.update(chunk)

    return sha1_hash.hexdigest()


def calculate_sha256(file_path: str, buffer_size: int = 8192) -> str:
    """计算文件的 SHA256 哈希值。"""
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as file:
        while chunk := file.read(buffer_size):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def calculate_hash(file_path: str, buffer_size: int = 8192) -> dict[str, str]:
    """同时计算文件的 MD5、SHA1、SHA256 哈希值。"""
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as file:
        while chunk := file.read(buffer_size):
            md5_hash.update(chunk)
            sha1_hash.update(chunk)
            sha256_hash.update(chunk)

    return dict(
        md5=md5_hash.hexdigest(),
        sha1=sha1_hash.hexdigest(),
        sha256=sha256_hash.hexdigest()
    )


if __name__ == '__main__':
    print(calculate_hash("text_tool.py"))
    print(get_file_size("text_tool.py", "mb"))
    print(read_yaml_file("config.yaml"))
