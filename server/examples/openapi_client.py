#!/usr/bin/env python3
"""开放平台 HanJiang-1 签名调用示例客户端（演示 / 对接参考）。

特性：
    - 支持 plain（AppId + AppKey 明文）与 hmac（HanJiang-1 签名）两种鉴权模式；
    - 凭证注入优先级：命令行参数 > 环境变量 > 文件内置演示常量；
    - ``--verbose`` 模式打印完整签名串与 HMAC 签名值，直观展示签名机制；
    - 默认仅演示单个 GET 请求（展示最简签名串）；可选 --with-post
      演示 POST / DELETE 全链路（创建用户后自动清理，不留脏数据）。

签名协议（与服务端实现严格对齐）：
    签名串 = HanJiang-1 + METHOD + URI + Content-Type + Date + SHA256(body)
    - URI：完整路径 + 查询串（不含域名），必须包含 /api/open/v1 前缀；
    - Content-Type：固定 application/json，与请求是否携带 body 无关；
    - Date：RFC1123 GMT 格式，经 X-App-Date 请求头传递；
    - body 为空时，SHA256(body) 部分取空字符串。

使用方式：
    python examples/openapi_client.py [--app-id APP_ID] [--app-key APP_KEY]
        [--mode plain|hmac] [--base-url URL] [--timeout 10]
        [--verbose] [--with-post]

环境变量：
    OPENAPI_APP_ID / OPENAPI_APP_KEY / OPENAPI_AUTH_MODE /
    OPENAPI_BASE_URL / OPENAPI_TIMEOUT / OPENAPI_VERBOSE

前提：
    1. 后端服务已启动（默认 http://127.0.0.1:8000）；
    2. 已在管理端创建开放应用并取得 AppId / AppKey；
    3. 应用已授权所需 scope（GET 演示需 user:read，POST 演示需 user:write）。
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import textwrap
import time
from dataclasses import dataclass
from email.utils import formatdate
from typing import Any, Final

import requests

# ── 协议常量（与服务端 src/constants/constants.py 保持一致，禁止单独修改）────
ALGORITHM: Final[str] = "HanJiang-1"  # 签名算法版本号（Ver）
SIGN_CONTENT_TYPE: Final[str] = "application/json"  # 签名串中 Content-Type 固定值
API_BASE_PATH: Final[str] = "/api/open/v1"  # 签名串使用的 URI 前缀（含版本号）
DEFAULT_BASE_URL: Final[str] = f"http://127.0.0.1:8000{API_BASE_PATH}"
DEFAULT_TIMEOUT: Final[float] = 10.0  # 请求超时（秒）

# ── 凭证注入环境变量名 ────────────────────────────────
ENV_APP_ID: Final[str] = "OPENAPI_APP_ID"
ENV_APP_KEY: Final[str] = "OPENAPI_APP_KEY"
ENV_AUTH_MODE: Final[str] = "OPENAPI_AUTH_MODE"
ENV_BASE_URL: Final[str] = "OPENAPI_BASE_URL"
ENV_TIMEOUT: Final[str] = "OPENAPI_TIMEOUT"
ENV_VERBOSE: Final[str] = "OPENAPI_VERBOSE"

# ── 请求头字段名（与服务端一致）───────────────────────
HEADER_APP_ID: Final[str] = "X-App-Id"
HEADER_APP_KEY: Final[str] = "X-App-Key"
HEADER_DATE: Final[str] = "X-App-Date"
HEADER_AUTHORIZATION: Final[str] = "X-App-Authorization"

# ── 演示内置凭证（仅供本地演示，正式对接请换成你自己的应用凭证）──────────
DEMO_APP_ID: Final[str] = "hj_530853d017a013b35a76"
DEMO_APP_KEY: Final[str] = "QO3j6i-TOiVGGAs2JPo0q-9iAQYL_-9E3xD5Kv36_WYLkoL4uNx50wXd0wqb__nd"
DEMO_AUTH_MODE: Final[str] = "hmac"


@dataclass(frozen=True)
class OpenApiConfig:
    """开放平台客户端配置。

    Attributes:
        app_id: 开放应用 AppId。
        app_key: 开放应用 AppKey（明文模式直接作为凭证，hmac 模式作为签名密钥）。
        auth_mode: 鉴权模式，plain 或 hmac。
        base_url: 服务端地址（含 /api/open/v1 前缀）。
        timeout: 单次请求超时秒数。
        verbose: 是否打印签名串与签名值等调试信息。
    """

    app_id: str
    app_key: str
    auth_mode: str = DEMO_AUTH_MODE
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    verbose: bool = False

    def __post_init__(self) -> None:
        """构造后校验配置合法性，配置错误立即报错而非带病运行。"""
        if not self.app_id or not self.app_key:
            raise ValueError("app_id 与 app_key 不能为空，请通过参数 / 环境变量注入")
        if self.auth_mode not in ("plain", "hmac"):
            raise ValueError(f"auth_mode 仅支持 plain / hmac，当前为: {self.auth_mode}")
        if self.timeout <= 0:
            raise ValueError(f"timeout 必须大于 0，当前为: {self.timeout}")


class OpenApiClient:
    """HanJiang-1 开放平台 API 客户端（演示参考实现）。

    封装请求签名、请求发送与统一响应处理。GET / POST / PUT / PATCH / DELETE
    均可直接使用；hmac 模式下自动完成签名，plain 模式下自动携带明文凭证。

    Raises:
        requests.RequestException: 网络层错误（连接失败、超时等）。
    """

    def __init__(self, config: OpenApiConfig) -> None:
        """初始化客户端。

        Args:
            config: 客户端配置（见 :class:`OpenApiConfig`）。
        """
        self._config = config

    # ── 签名工具 ──────────────────────────────────────

    def _sha256_hex(self, text: str) -> str:
        """计算 UTF-8 文本的 SHA-256 十六进制摘要。

        Args:
            text: 待哈希文本。

        Returns:
            64 位小写十六进制哈希串。
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def build_signing_string(self, method: str, uri: str, date: str, body: bytes = b"") -> str:
        """构造 HanJiang-1 待签名串（公开方法，便于 --verbose 演示打印）。

        格式：Ver + METHOD + URI + Content-Type + Date + SHA256(body)，直接拼接无分隔符。

        Args:
            method: HTTP 方法（GET/POST/PUT/PATCH/DELETE）。
            uri: 完整路径 + 查询串（不含域名，含 /api/open/v1 前缀）。
            date: RFC1123 GMT 时间；必须与 X-App-Date 请求头为同一值（单点生成）。
            body: 请求体字节流；为空时 body 哈希取空字符串。

        Returns:
            参与 HMAC 计算的原始签名串。
        """
        body_hash = self._sha256_hex(body.decode("utf-8")) if body else ""
        signing_string = "".join(
            [ALGORITHM, method.upper(), uri, SIGN_CONTENT_TYPE, date, body_hash]
        )
        if self._config.verbose:
            print(f"        ┌ 签名串: {signing_string}")
            print(f"        └ X-App-Date: {date}")
        return signing_string

    def build_headers(self, method: str, uri: str, body: bytes = b"") -> dict[str, str]:
        """根据鉴权模式构造完整请求头。

        Args:
            method: HTTP 方法。
            uri: 完整路径 + 查询串（不含域名）。
            body: 请求体字节流（用于 body 哈希）。

        Returns:
            可直接附加到 requests 请求的请求头字典。

        Raises:
            ValueError: auth_mode 非法（构造时已拦截，此处为防御性校验）。
        """
        headers: dict[str, str] = {HEADER_APP_ID: self._config.app_id}

        if self._config.auth_mode == "plain":
            headers[HEADER_APP_KEY] = self._config.app_key
            return headers

        date_str = formatdate(timeval=None, usegmt=True)  # 单点生成：签名串与 X-App-Date 必须一致
        signing_string = self.build_signing_string(method, uri, date_str, body)
        signature = hmac.new(
            self._config.app_key.encode("utf-8"),
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if self._config.verbose:
            print(f"        ┌ X-App-Authorization: {ALGORITHM} {self._config.app_id}:{signature}")

        headers[HEADER_DATE] = date_str
        headers[HEADER_AUTHORIZATION] = f"{ALGORITHM} {self._config.app_id}:{signature}"
        # 请求头统一携带 Content-Type（GET 无 body 也带，与服务端签名校验约定一致）
        headers["Content-Type"] = SIGN_CONTENT_TYPE
        return headers

    # ── 请求封装 ──────────────────────────────────────

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """发送已签名的 HTTP 请求。

        Args:
            method: HTTP 方法（不区分大小写）。
            path: 接口路径（以 / 开头；query 直接拼在 path 或通过 params 传入）。
            body: 请求体（dict 自动序列化为 JSON）。
            params: URL 查询参数（requests 自动编码）。

        Returns:
            requests.Response 原始响应对象。

        Raises:
            requests.RequestException: 连接失败或超时等网络层异常。
        """
        url = f"{self._config.base_url}{path}"
        body_bytes = b""
        if body is not None:
            body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        # uri = 完整路径 + query（不含域名），必须包含 /api/open/v1 前缀，
        # 否则两端签名串不一致导致 HMAC 鉴权失败。
        query_str = ""
        if params:
            query_str = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        uri = f"{API_BASE_PATH}{path}{query_str}"

        headers = self.build_headers(method, uri, body=body_bytes)
        return requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=body_bytes if body_bytes else None,
            timeout=self._config.timeout,
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        """发送 GET 请求（自动签名）。"""
        return self.request("GET", path, params=params)

    def post(self, path: str, body: dict[str, Any]) -> requests.Response:
        """发送 POST 请求（自动签名）。"""
        return self.request("POST", path, body=body)

    def delete(self, path: str) -> requests.Response:
        """发送 DELETE 请求（自动签名）。"""
        return self.request("DELETE", path)


# ── 演示辅助 ──────────────────────────────────────────


def _print_step(index: int, title: str) -> None:
    """打印演示步骤标题。

    Args:
        index: 步骤序号。
        title: 步骤描述。
    """
    print(f"\n[{index}] {title}")


def _format_json(obj: object) -> str:
    """将 Python 对象格式化为可读 JSON 文本（2 空格缩进，中文不转义）。

    Args:
        obj: 待格式化的对象（dict / list 等）。

    Returns:
        格式化后的多行 JSON 字符串。
    """
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _print_response(resp: requests.Response, summary_key: str | None = None) -> None:
    """统一打印响应：成功时格式化输出 JSON，失败时给出排查提示。

    Args:
        resp: 待展示的响应对象。
        summary_key: 响应 data 中需要精简展示的字段路径（如 "items"），
            缺省时格式化输出 data 全量（适用于小体量响应）。
    """
    print(f"    状态码: {resp.status_code}")
    if resp.status_code >= 400:
        try:
            err = resp.json()
            print(f"    错误信息:\n{textwrap.indent(_format_json(err), '    ')}")
        except ValueError:
            print(f"    响应体: {resp.text}")
        if resp.status_code == 401:
            print(
                "    ── 鉴权失败排查指引 ──────────────────────────\n"
                "    1. AppId / AppKey 是否正确（含前后空格）；\n"
                "    2. 系统时间是否与服务器同步（签名时间窗 300 秒）；\n"
                "    3. 签名协议版本是否与服务端一致（Content-Type 固定 application/json）；\n"
                "    4. 应用 auth_mode 是否与客户端一致（plain / hmac）。"
            )
        return

    data = resp.json().get("data")
    if summary_key and isinstance(data, dict):
        items = data.get(summary_key)
        if isinstance(items, list):
            print(f"    返回: {summary_key} {len(items)} 条")
            for item in items[:3]:
                print(f"        - id={item.get('id')} username={item.get('username')} name={item.get('name')}")
            if len(items) > 3:
                print(f"        ... 共 {len(items)} 条，total={data.get('total')}")
            return
    print(f"    返回:\n{textwrap.indent(_format_json(resp.json()), '    ')}")


# ── 命令行与配置解析 ──────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    Args:
        argv: 命令行参数列表；None 时取 sys.argv[1:]。

    Returns:
        解析后的参数命名空间。
    """
    parser = argparse.ArgumentParser(
        description="开放平台 HanJiang-1 签名调用示例（演示 / 对接参考）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--app-id", default=os.getenv(ENV_APP_ID), help="开放应用 AppId")
    parser.add_argument("--app-key", default=os.getenv(ENV_APP_KEY), help="开放应用 AppKey")
    parser.add_argument("--mode", default=os.getenv(ENV_AUTH_MODE, DEMO_AUTH_MODE), help="鉴权模式: plain|hmac")
    parser.add_argument("--base-url", default=os.getenv(ENV_BASE_URL, DEFAULT_BASE_URL), help="服务端地址")
    parser.add_argument("--timeout", type=float, default=float(os.getenv(ENV_TIMEOUT, DEFAULT_TIMEOUT)), help="请求超时秒数")
    parser.add_argument("--verbose", action="store_true", default=os.getenv(ENV_VERBOSE) == "1", help="打印签名串与签名值")
    parser.add_argument("--with-post", action="store_true", help="额外演示 POST 创建 + DELETE 清理（需 user:write scope）")
    return parser.parse_args(argv)


def _build_config(args: argparse.Namespace) -> OpenApiConfig:
    """由命令行参数构造客户端配置（凭证优先级：参数 > 环境变量 > 内置演示常量）。

    Args:
        args: 解析后的命令行参数。

    Returns:
        校验通过的客户端配置。
    """
    return OpenApiConfig(
        app_id=args.app_id or DEMO_APP_ID,
        app_key=args.app_key or DEMO_APP_KEY,
        auth_mode=args.mode,
        base_url=args.base_url,
        timeout=args.timeout,
        verbose=args.verbose,
    )


# ── 主演示流程 ────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """运行开放平台 API 调用演示。

    Args:
        argv: 命令行参数；None 时取 sys.argv[1:]。

    Returns:
        进程退出码（0 成功；1 失败）。
    """
    args = _parse_args(argv)
    config = _build_config(args)
    client = OpenApiClient(config)

    print(f"汉江开放平台 API 调用演示开始")
    print(f"服务端地址: {config.base_url}")
    print(f"鉴权模式: {config.auth_mode}")
    print(f"应用标识（AppId）: {config.app_id}")
    print(f"应用密钥（AppKey）: {config.app_key}")
    print("=" * 64)

    try:
        # 1.（默认）健康检查——演示最简 GET 签名（无 body、无 query）
        _print_step(1, "GET /health")
        resp = client.get("/health")
        _print_response(resp)

        # 2.（可选）POST 创建用户 + DELETE 清理——演示带 body 的签名
        if args.with_post:
            _print_step(2, "POST /users + DELETE /users/{id}（演示带 body 签名，创建后自动清理）")
            username = f"demo_{int(time.time())}"
            resp = client.post("/users", body={"username": username, "email": f"{username}@demo.local", "name": "演示用户"})
            _print_response(resp)
            if resp.status_code in (200, 201):
                user_id = resp.json()["data"]["id"]
                print(f"    已创建用户 id={user_id}，正在清理…")
                resp = client.delete(f"/users/{user_id}")
                _print_response(resp)
    except requests.RequestException as exc:
        print(f"请求失败: {exc}")
        print("请确认后端服务已启动且网络可达（--base-url 可指定其他地址）。")
        return 1

    print("\n" + "=" * 64)
    print("演示结束")

    return 0


if __name__ == "__main__":
    sys.exit(main())