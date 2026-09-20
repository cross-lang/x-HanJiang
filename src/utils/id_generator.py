#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ID 生成模块

提供 UUID 与基于时间戳的唯一 ID 生成方法，便于在业务中快速生成标识符。
"""

import uuid
import time
import secrets


def gen_uuid() -> str:
    """生成 UUID4 字符串。"""
    return str(uuid.uuid4())


def gen_timestamp_id() -> int:
    """生成基于时间戳的唯一 ID（微秒级 + 随机后缀）。"""
    micros = time.time_ns() // 1_000
    return int(micros) + secrets.randbelow(9000) + 1000


if __name__ == '__main__':
    print(gen_uuid())
    print(gen_timestamp_id())
