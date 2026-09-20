#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
正则表达式模式模块

提供常用的正则表达式模式（如 IP、MAC 地址匹配），以便在项目中统一复用。
"""

import re

_IP_RE: re.Pattern[str] = re.compile(
    r"^(([01]?\d\d?|2[0-4]\d|25[0-5])\.){3}([01]?\d\d?|2[0-4]\d|25[0-5])$"
)
_MAC_RE: re.Pattern[str] = re.compile(r"^([0-9a-fA-F]{2}[:]){5}[0-9a-fA-F]{2}$")


def match_ip() -> re.Pattern[str]:
    """匹配 IP 地址的正则模式。"""
    return _IP_RE


def match_mac() -> re.Pattern[str]:
    """匹配 MAC 地址的正则模式。"""
    return _MAC_RE
