#!/usr/bin/env python3
"""utils.helpers.get_client_ip 单元测试。

统一约定：只读取反向代理写入的 X-Real-IP 头；
无头或空值时返回空字符串，不回退 TCP 连接地址或其他转发头。
"""

from starlette.requests import Request


def _make_request(headers: dict[str, str]) -> Request:
    """构造最小可用的 Starlette 请求对象。

    Args:
        headers: HTTP 请求头
    """
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 54321),
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


class TestGetClientIp:
    """get_client_ip 取 IP 逻辑测试。"""

    def test_returns_x_real_ip(self) -> None:
        """存在 X-Real-IP 时直接返回该值。"""
        from src.utils.helpers import get_client_ip

        req = _make_request({"X-Real-IP": "203.0.113.10"})
        assert get_client_ip(req) == "203.0.113.10"

    def test_strips_whitespace(self) -> None:
        """X-Real-IP 值首尾空白被去除。"""
        from src.utils.helpers import get_client_ip

        req = _make_request({"X-Real-IP": "  203.0.113.11  "})
        assert get_client_ip(req) == "203.0.113.11"

    def test_missing_header_returns_empty(self) -> None:
        """无 X-Real-IP（本地直连/代理未写入）时返回空字符串。"""
        from src.utils.helpers import get_client_ip

        req = _make_request({})
        assert get_client_ip(req) == ""

    def test_blank_header_returns_empty(self) -> None:
        """X-Real-IP 为纯空白时返回空字符串。"""
        from src.utils.helpers import get_client_ip

        req = _make_request({"X-Real-IP": "   "})
        assert get_client_ip(req) == ""

    def test_ignores_x_forwarded_for_fallback(self) -> None:
        """只有 X-Forwarded-For 而无 X-Real-IP 时不回退，仍返回空字符串。"""
        from src.utils.helpers import get_client_ip

        req = _make_request({"X-Forwarded-For": "203.0.113.12, 10.0.0.1"})
        assert get_client_ip(req) == ""
