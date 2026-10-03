#!/usr/bin/env python3
"""HanJiang-1 开放接口签名 / 解签工具（协议层纯函数，无 FastAPI / DB 依赖）。

服务端与调用方共用同一协议（与 examples/openapi_client.py、集成文档严格对齐）：
    签名串 = Ver + METHOD + URI + Content-Type + Date + SHA256(body)
    签名值 = HMAC-SHA256(AppKey, 签名串)
约定细节：
    - URI：完整路径 + 查询串（不含域名），必须包含 /api/open/v1 前缀；
    - Content-Type：固定 application/json，与请求是否携带 body 无关；
    - Date：RFC1123 GMT 格式，经 X-App-Date 请求头传递；
    - body 为空时，SHA256(body) 部分取空字符串。

本模块只做协议计算；应用查询 / 审批门槛 / 密钥解密由网关服务
（src/services/open/gateway_service.py）负责；HTTP 头/请求体剥离由
API 层（src/api/dependencies.py）负责。
"""

from datetime import UTC, datetime

from src.constants.constants import (
    OPENAPI_ALGORITHM,
    OPENAPI_CONTENT_TYPE,
    OPENAPI_SIGNATURE_WINDOW_SECONDS,
)
from src.utils import security
from src.utils.time import parse_http_date


def build_signing_string(
    *,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
) -> str:
    """构造 HanJiang-1 待签名串（与外部调用方的协议约定，勿随意改）。

    格式：Ver + METHOD + URI + Content-Type + Date + SHA256(body)，直接拼接无分隔符。
    Content-Type 固定为 application/json（与请求是否携带 body 无关），
    GET 无 body 时同样拼接该固定值，body 为空则 SHA256(body) 取空字符串。
    """
    body_hash = security.sha256_hex(body.decode("utf-8")) if body else ""
    return "".join(
        [
            OPENAPI_ALGORITHM,
            method.upper(),
            uri,
            content_type,
            date,
            body_hash,
        ]
    )


def sign(
    *,
    app_key: str,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
) -> str:
    """HMAC-SHA256 签名（开放接口调用方侧逻辑，供测试 / 对接参考）。

    与 examples/openapi_client.py 的签名实现等价：
        hmac.new(app_key, signing_string, hashlib.sha256).hexdigest()
    """
    return security.hmac_sha256_hex(
        app_key,
        build_signing_string(method=method, uri=uri, content_type=content_type, date=date, body=body),
    )


def verify_signature(
    *,
    app_key: str,
    method: str,
    uri: str,
    content_type: str,
    date: str,
    body: bytes,
    signature: str,
) -> bool:
    """解签校验：以 AppKey 重算签名并与调用方签名常量时间比对。

    参数与 build_signing_string / sign 完全同源，调用方务必传入与
    请求头 X-App-Date / 原始 body 一致的值，否则校验必然失败。
    """
    expected = sign(app_key=app_key, method=method, uri=uri, content_type=content_type, date=date, body=body)
    return security.constant_time_equals(expected, signature)


def is_request_date_valid(
    date_str: str,
    *,
    window_seconds: int = OPENAPI_SIGNATURE_WINDOW_SECONDS,
) -> bool:
    """校验 X-App-Date 是否落在当前时间窗内（防重放）。

    时间窗绝对值超出 window_seconds 即判定失效；日期格式非法同样返回 False。
    """
    request_time = parse_http_date(date_str)
    if request_time is None:
        return False
    now = datetime.now(UTC)
    return abs((now - request_time).total_seconds()) <= window_seconds


__all__ = [
    "build_signing_string",
    "sign",
    "verify_signature",
    "is_request_date_valid",
]
