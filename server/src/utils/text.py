#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文本处理模块

提供字符串检索（KMP）、中文字符检测、哈希计算、CRC32 计算、汉字转拼音等常用文本工具方法。
"""

import re
import zlib
import difflib
import hashlib

from pypinyin import Style, pinyin
from typing import Any


NUM_ARABIC_TO_CH_MAP: dict[int, str] = {
    0: '零',
    1: '一',
    2: '二',
    3: '三',
    4: '四',
    5: '五',
    6: '六',
    7: '七',
    8: '八',
    9: '九'
}

NUM_CH_TO_ARABIC_MAP: dict[str, int] = {
    '零': 0,
    '一': 1,
    '二': 2,
    '三': 3,
    '四': 4,
    '五': 5,
    '六': 6,
    '七': 7,
    '八': 8,
    '九': 9
}

NUM_ARABIC_TO_TRA_CH_MAP: dict[int, str] = {
    0: '零',
    1: '壹',
    2: '贰',
    3: '叁',
    4: '肆',
    5: '伍',
    6: '陆',
    7: '柒',
    8: '捌',
    9: '玖'
}


def get_same_start_end(pattern: str) -> list[int]:
    """获取最长前后缀相同的字符位数。"""
    n = len(pattern)
    result_list: list[int] = [0] * n

    if n <= 1:
        return result_list

    i = 2
    while i < n:
        if pattern[i - 1] == pattern[result_list[i - 1]]:
            result_list[i] = result_list[i - 1] + 1
        i += 1
    return result_list


def match_sub_str(string: str, pattern: str) -> int:
    """使用 KMP 算法在字符串中搜索子串。返回起始索引，未找到返回 -1。"""
    s_length = len(string)
    p_length = len(pattern)
    i = 0
    j = 0
    next_list = get_same_start_end(pattern)
    while i < s_length:
        if string[i] == pattern[j]:
            if j == p_length - 1:
                return i + 1 - p_length
            else:
                i += 1
                j += 1
        else:
            if j == 0:
                i += 1
            else:
                j = next_list[j]
    return -1


def is_str(value: Any) -> bool:
    """判断变量的值是否为字符串。"""
    return isinstance(value, (str, bytes))


def is_all_chinese(value: str) -> bool:
    """检验是否全是中文字符。"""
    for _char in value:
        if not u'\u4e00' <= _char <= u'\u9fff':
            return False
    return True


def is_contains_chinese(value: str) -> bool:
    """检验是否含有中文字符。"""
    for _char in value:
        if u'\u4e00' <= _char <= u'\u9fff':
            return True
    return False


def is_md5_value(value: str) -> bool:
    """检查是否为 32 个十六进制字符（MD5）。"""
    md5_pattern = re.compile(r"^[0-9a-fA-F]{32}$")
    return bool(md5_pattern.match(value))


def is_sha1_value(value: str) -> bool:
    """检查是否为 40 个十六进制字符（SHA1）。"""
    sha1_pattern = re.compile(r"^[0-9a-fA-F]{40}$")
    return bool(sha1_pattern.match(value))


def is_sha256_value(value: str) -> bool:
    """检查是否为 64 个十六进制字符（SHA256）。"""
    sha256_pattern = re.compile(r"^[0-9a-fA-F]{64}$")
    return bool(sha256_pattern.match(value))


def calculate_crc32(value: str) -> int:
    """计算 CRC32 值。"""
    return zlib.crc32(value.encode("utf-8"))


def calculate_md5(value: str) -> str:
    """计算字符串的 MD5 哈希。"""
    md5_hash = hashlib.md5()
    md5_hash.update(value.encode("utf-8"))
    return md5_hash.hexdigest()


def calculate_sha1(value: str) -> str:
    """计算字符串的 SHA1 哈希。"""
    sha1_hash = hashlib.sha1()
    sha1_hash.update(value.encode("utf-8"))
    return sha1_hash.hexdigest()


def calculate_sha256(value: str) -> str:
    """计算字符串的 SHA256 哈希。"""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(value.encode("utf-8"))
    return sha256_hash.hexdigest()


def get_char_max_index(text: str, char: str) -> int:
    """获取文本中某字符的最大索引。"""
    return max((i for i, _ in enumerate(text) if _ == char))


def string_similar(str1: str, str2: str) -> float:
    """计算文本相似度。"""
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


def convert_ch_to_arabic(text: str) -> str:
    """将文本中的汉字数字转换为阿拉伯数字。"""
    return (
        "".join(
            (
                str(NUM_CH_TO_ARABIC_MAP.get(_))
                if _ in NUM_CH_TO_ARABIC_MAP.keys() else _
                for _ in text
            )
        )
    )


def hanzi_to_pinyin(hanzi_name: str) -> str:
    """汉字转为拼音（基础版）。"""
    return (
        "".join(
            (
                pinyin_ls[0]
                for pinyin_ls
                in pinyin(
                    hanzi_name,
                    style=Style.NORMAL,
                    errors='ignore',
                    strict=False,
                    heteronym=True
                )
            )
        )
    )


def advanced_hanzi_to_pinyin(hanzi_name: str) -> str:
    """汉字转为拼音（高级版，阿拉伯数字先转汉字再转拼音）。"""
    str_arabic_list = [str(_) for _ in NUM_ARABIC_TO_TRA_CH_MAP.keys()]

    return (
        "".join(
            (
                pinyin_ls[0]
                for pinyin_ls
                in pinyin(
                    "".join(
                        (
                            NUM_ARABIC_TO_TRA_CH_MAP[int(_)]
                            if _.isdigit() and _ in str_arabic_list else _
                            for _ in hanzi_name
                        )
                    ),
                    style=Style.NORMAL,
                    errors='ignore',
                    strict=False,
                    heteronym=True
                )
            )
        )
    )


if __name__ == '__main__':
    print(is_str(u"xxx"))
    print(is_contains_chinese("我们中国ss"))
    print(is_all_chinese("我们中国ss"))
    print(is_contains_chinese("ss"))
    print(is_all_chinese("ss"))
    print(calculate_crc32("106.75.54.33"))
    print(calculate_crc32("2.57.122.123"))
    print(calculate_md5("2.57.122.123"))
    print(calculate_sha1("2.57.122.123"))
    print(calculate_sha256("2.57.122.123"))
    print(is_md5_value("7daad22ca20b7fef23fea40ba37d0315"))
    print(is_sha256_value("045bb77ae9f41e4e8df7681af68c7ad4ede3ebc27dbd9dfbf79e3bdc674023f3"))
