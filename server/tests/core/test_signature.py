#!/usr/bin/env python3
"""
开放接口签名 / 解签工具测试（src/core/signature.py）

协议约定（与 examples/openapi_client.py 严格对齐）：
    签名串 = Ver + METHOD + URI + Content-Type + Date + SHA256(body)
    签名值 = HMAC-SHA256(AppKey, 签名串)
覆盖构造、签名、验签全分支与时间窗防重放。
"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from src.constants.constants import OPENAPI_ALGORITHM
from src.core.signature import (
    build_signing_string,
    is_request_date_valid,
    sign,
    verify_signature,
)

# 一组固定的协议参数，供各用例复用
_METHOD = "POST"
_URI = "/api/open/v1/apps"
_CONTENT_TYPE = "application/json"
_DATE = "Wed, 21 Oct 2015 07:28:00 GMT"
_BODY = b'{"name":"demo"}'
_APP_KEY = "app-key-001"


class TestBuildSigningString:
    """待签名串构造。"""

    def test_concatenates_all_parts_with_body_hash(self) -> None:
        """带 body：Ver + 大写方法 + URI + Content-Type + Date + SHA256(body) 直接拼接。"""
        body_hash = hashlib.sha256(_BODY.decode("utf-8").encode("utf-8")).hexdigest()
        expected = "".join([OPENAPI_ALGORITHM, "POST", _URI, _CONTENT_TYPE, _DATE, body_hash])
        assert (
            build_signing_string(method=_METHOD, uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=_BODY)
            == expected
        )

    def test_empty_body_yields_empty_hash(self) -> None:
        """GET 等无 body 场景：body 为空时 SHA256 部分取空字符串。"""
        result = build_signing_string(method="get", uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=b"")
        assert result.endswith(_DATE)  # 之后无任何字符
        assert result.startswith(OPENAPI_ALGORITHM + "GET")  # 方法统一转大写

    def test_uppercase_method(self) -> None:
        """方法不论大小写都转成大写参与签名。"""
        upper = build_signing_string(method="POST", uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=b"x")
        lower = build_signing_string(method="post", uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=b"x")
        assert upper == lower


class TestSignAndVerify:
    """签名生成与校验。"""

    def test_sign_matches_hmac_primitive(self) -> None:
        """sign 结果应等于按协议手工计算的 HMAC-SHA256。"""
        signing_string = build_signing_string(
            method=_METHOD, uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=_BODY
        )
        expected = hmac.new(_APP_KEY.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256).hexdigest()
        assert (
            sign(app_key=_APP_KEY, method=_METHOD, uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=_BODY)
            == expected
        )

    def test_verify_correct_signature_passes(self) -> None:
        """用相同参数重算并比对：合法签名返回 True。"""
        signature = sign(app_key=_APP_KEY, method=_METHOD, uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=_BODY)
        assert (
            verify_signature(
                app_key=_APP_KEY,
                method=_METHOD,
                uri=_URI,
                content_type=_CONTENT_TYPE,
                date=_DATE,
                body=_BODY,
                signature=signature,
            )
            is True
        )

    def test_verify_tampered_body_fails(self) -> None:
        """body 被篡改 → 重算签名不一致 → False。"""
        signature = sign(app_key=_APP_KEY, method=_METHOD, uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=_BODY)
        assert (
            verify_signature(
                app_key=_APP_KEY,
                method=_METHOD,
                uri=_URI,
                content_type=_CONTENT_TYPE,
                date=_DATE,
                body=b'{"name":"attacker"}',
                signature=signature,
            )
            is False
        )

    def test_verify_wrong_app_key_fails(self) -> None:
        """AppKey 不同 → 验签失败。"""
        signature = sign(app_key=_APP_KEY, method=_METHOD, uri=_URI, content_type=_CONTENT_TYPE, date=_DATE, body=_BODY)
        assert (
            verify_signature(
                app_key="another-key",
                method=_METHOD,
                uri=_URI,
                content_type=_CONTENT_TYPE,
                date=_DATE,
                body=_BODY,
                signature=signature,
            )
            is False
        )

    def test_verify_bad_signature_string_fails(self) -> None:
        """签名串本身格式错误 → 常量时间比对后返回 False。"""
        assert (
            verify_signature(
                app_key=_APP_KEY,
                method=_METHOD,
                uri=_URI,
                content_type=_CONTENT_TYPE,
                date=_DATE,
                body=_BODY,
                signature="not-a-valid-signature",
            )
            is False
        )


class TestRequestDateWindow:
    """时间窗防重放。"""

    def test_current_date_is_valid(self) -> None:
        """当前时间生成的 RFC1123 日期落在窗口内。"""
        now_str = format_datetime(datetime.now(UTC))
        assert is_request_date_valid(now_str) is True

    def test_stale_date_is_invalid(self) -> None:
        """超出窗口（默认 300 秒）的历史日期判定失效。"""
        stale = format_datetime(datetime.now(UTC) - timedelta(seconds=1000))
        assert is_request_date_valid(stale) is False

    def test_future_date_is_invalid(self) -> None:
        """超前过多的日期（重放/时钟漂移）同样判定失效。"""
        future = format_datetime(datetime.now(UTC) + timedelta(seconds=1000))
        assert is_request_date_valid(future) is False

    def test_garbage_date_is_invalid(self) -> None:
        """非法日期格式返回 False，不抛异常。"""
        assert is_request_date_valid("not-a-date") is False
        assert is_request_date_valid("") is False
