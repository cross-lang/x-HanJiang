#!/usr/bin/env python3
"""开放平台 API 调用示例（支持 plain / hmac 两种鉴权模式）。

使用方式：
    python examples/openapi_demo.py

前提：
    1. 后端服务已启动（默认 http://127.0.0.1:8000）
    2. 已创建开放应用，拿到 app_id 和 app_key
    3. 根据应用的 auth_mode 修改下面的 AUTH_MODE
"""

import hashlib
import hmac
from datetime import datetime, timezone
from email.utils import formatdate

import requests

# ── 配置 ──────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/api/open/v1"
APP_ID = "hj_56d27bdcd134c3b68856"
APP_KEY = "nE-rQkkAUw8P6Bd3-eRYL2LXzdHJ-v6BcY_bPW61N54REk0D-vAHMHj-98TI9mBy"

# 鉴权模式：plain | hmac
AUTH_MODE = "hmac"


# ── HMAC 签名工具 ────────────────────────────────────

def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_headers(method: str, uri: str, body: bytes = b"", content_type: str = "") -> dict:
    """根据鉴权模式构造请求头。

    plain 模式：X-App-Id + X-App-Key
    hmac  模式：X-App-Id + X-App-Date + X-App-Authorization
    """
    headers = {"X-App-Id": APP_ID}

    if AUTH_MODE == "plain":
        headers["X-App-Key"] = APP_KEY
        return headers

    # ── HMAC 模式 ──
    date_str = formatdate(timeval=None, usegmt=True)  # 如 "Sun, 27 Sep 2026 08:00:00 GMT"

    body_hash = _sha256_hex(body.decode("utf-8")) if body else ""
    signing_string = "".join([
        "HanJiang-1",
        method.upper(),
        uri,
        content_type,
        date_str,
        body_hash,
    ])

    signature = hmac.new(
        APP_KEY.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers["X-App-Date"] = date_str
    headers["X-App-Authorization"] = f"HanJiang-1 {APP_ID}:{signature}"
    return headers


def call(method: str, path: str, body: dict | None = None):
    """发请求并自动签名。"""
    url = f"{BASE_URL}{path}"
    body_bytes = b""
    content_type = ""

    if body is not None:
        import json
        body_bytes = json.dumps(body).encode("utf-8")
        content_type = "application/json"

    # uri = path + query（不含域名）
    uri = path
    headers = build_headers(method, uri, body=body_bytes, content_type=content_type)
    if content_type:
        headers["Content-Type"] = content_type

    resp = requests.request(method, url, headers=headers, data=body_bytes if body_bytes else None)
    return resp


# ── 主流程 ────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"开放平台 API 调用示例（鉴权模式: {AUTH_MODE}）")
    print("=" * 60)

    # 1. 健康检查
    print("\n[1] GET /health")
    r = call("GET", "/health")
    print(f"    状态码: {r.status_code}")
    print(f"    返回: {r.json()}")

    # 2. 版本信息
    print("\n[2] GET /version")
    r = call("GET", "/version")
    print(f"    状态码: {r.status_code}")
    print(f"    返回: {r.json()}")

    # 3. 连通性测试
    print("\n[3] GET /ping")
    r = call("GET", "/ping")
    print(f"    状态码: {r.status_code}")
    print(f"    返回: {r.json()}")

    # 4. 用户列表
    print("\n[4] GET /users?page=1&page_size=5")
    r = call("GET", "/users?page=1&page_size=5")
    print(f"    状态码: {r.status_code}")
    print(f"    返回: {r.json()}")

    print("\n" + "=" * 60)
    print("示例结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
