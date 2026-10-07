#!/usr/bin/env python3
"""通用工具函数模块（精简）。

保留项目中实际使用的通用函数：客户端 IP 提取、敏感数据脱敏、项目根目录定位；
其余（generate_request_id / datetime_now_iso）无引用，已于 2026-09-30 清理。
"""

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """提取客户端真实 IP（全项目唯一取 IP 入口）。

    统一约定：真实 IP 由前置反向代理（Nginx）通过 X-Real-IP 头写入
    （proxy_set_header X-Real-IP $remote_addr）；
    本函数只读取该头，不自行解析 X-Forwarded-For 或 TCP 连接地址。
    未经过反向代理（如本地直连开发）或代理未写该头时返回空字符串。

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 客户端真实 IP；获取不到时为空字符串 ""
    """
    return request.headers.get("X-Real-IP", "").strip()


def mask_sensitive(data: dict[str, Any], keys: list[str] | None = None) -> dict[str, Any]:
    """对字典中的敏感字段进行脱敏处理。
    将指定键的值替换为 "****"，用于安全日志输出。
    默认脱敏字段：password、secret、token、key、authorization。

    Args:
        data: 原始数据字典
        keys: 需要脱敏的键名列表（不区分大小写）

    Returns:
        dict[str, Any]: 脱敏后的数据副本（不修改原始数据）
    """
    default_keys: list[str] = ["password", "secret", "token", "key", "authorization"]
    sensitive_keys: set[str] = {k.lower() for k in (keys or default_keys)}
    masked: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            masked[k] = "****"
        elif isinstance(v, dict):
            masked[k] = mask_sensitive(v, keys)
        else:
            masked[k] = v
    return masked


def mask_url_credentials(url: str) -> str:
    """脱敏 URL 中的账号/密码凭据，用于安全日志输出。

    支持形如 ``mysql+pymysql://user:pass@host:3306/db`` 或
    ``redis://default:pass@host:6379/0`` 的连接串；
    密码统一替换为 ``***``，用户名保留以便排查。

    Args:
        url: 原始连接串（可能含明文账号密码）

    Returns:
        str: 脱敏后的连接串；解析失败时原样返回
    """
    try:
        parsed = urlsplit(url)
        if parsed.username is None and parsed.password is None:
            return url
        netloc: str = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        if parsed.username:
            netloc = f"{parsed.username}:***@{netloc}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except ValueError:
        return url


def find_project_root(marker: str = "pyproject.toml") -> Path:
    """从当前文件位置向上查找项目根目录。
    逐级向上遍历父目录，返回第一个包含 *marker* 文件的目录；
    若未找到，则回退到 ``<当前文件>/../../``（即 src 的上两级）。

    Args:
        marker: 用于标识项目根目录的文件名，默认 ``pyproject.toml``

    Returns:
        Path: 项目根目录的绝对路径
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / marker).exists():
            return parent
    return current.parent.parent
