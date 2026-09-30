# 开放平台对接指南

> 本文档面向需要调用汉江（HanJiang）开放平台 API 的外部开发者，覆盖鉴权协议、签名原理、端点清单与 Python / Go 对接步骤。
> 配套示例：`server/examples/openapi_client.py`（完整可运行的 Python 演示客户端）。

***

## 1. 概述

开放平台接口通过 **AppId / AppKey** 凭证体系对外暴露能力，支持两种鉴权模式：

| 模式      | 凭证传递方式                                                     | 适用场景          |
| ------- | ---------------------------------------------------------- | ------------- |
| `plain` | `X-App-Id` + `X-App-Key`（明文）                               | 内网可信环境、快速联调   |
| `hmac`  | `X-App-Id` + `X-App-Date` + `X-App-Authorization`（HMAC 签名） | 生产环境、公网调用（推荐） |

所有开放接口统一走 `/api/open/v1` 前缀，响应统一为 `BaseResp` 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-09-30T08:00:00.000000+00:00",
  "request_id": "xxxx"
}
```

## 2. 前置准备

1. 在管理端【系统管理 → 开放应用】创建应用，取得 **AppId / AppKey** 并选择鉴权模式（plain / hmac / both）；
2. 为应用勾选所需 **scope**（见第 6 节），scope 修改后需服务端重启生效（启动时自动同步）；
3. 确认服务端地址（默认 `http://127.0.0.1:8000`）与签名时间窗（默认 300 秒，见 `src/constants/constants.py`）。

> ⚠️ AppKey 是应用的密钥凭据：明文模式下直接作为凭证，hmac 模式下作为 HMAC 签名密钥。**严禁硬编码在客户端代码或前端页面**，建议通过环境变量 / 密钥管理系统注入。

## 3. HanJiang-1 HMAC 签名原理

### 3.1 签名串公式

```
签名串 = Ver + METHOD + URI + Content-Type + Date + SHA256(body)
```

各字段**直接拼接、无分隔符**：

| 字段             | 取值                                             | 示例                                      |
| -------------- | ---------------------------------------------- | --------------------------------------- |
| `Ver`          | 算法版本号，固定 `HanJiang-1`                          | `HanJiang-1`                            |
| `METHOD`       | HTTP 方法大写（GET/POST/PUT/PATCH/DELETE）           | `GET`                                   |
| `URI`          | 完整路径 + 查询串（**不含域名**，含 `/api/open/v1` 前缀）       | `/api/open/v1/users?page=1&page_size=5` |
| `Content-Type` | **固定** **`application/json`**（与请求是否携带 body 无关） | `application/json`                      |
| `Date`         | RFC1123 GMT 时间（即 `X-App-Date` 请求头值）            | `Tue, 30 Sep 2026 08:00:00 GMT`         |
| `SHA256(body)` | body 的 SHA-256 十六进制小写；**body 为空时取空字符串**        | `fc005f51...` 或 `（空）`                   |

### 3.2 签名值计算

```
signature = hex( HMAC-SHA256( key = AppKey, data = 签名串 ) )   # 小写十六进制
X-App-Authorization = "HanJiang-1 " + AppId + ":" + signature
```

### 3.3 URI 拼接规则（最容易踩坑）

- **必须包含** **`/api/open/v1`** **前缀**（不含域名）；
- **不含域名**：`http://127.0.0.1:8000` 不参与签名；
- **query 参与签名**，且必须保持**原始编码形式**（不做 URL 转义、不排序、不改写），服务端按收到的 raw query 原样比对；
- 带 body 的请求（如 POST）：`SHA256(body)` 使用**实际发送的字节流**计算。

### 3.4 完整签名串示例

`GET /api/open/v1/health`（无 body、无 query）：

```
HanJiang-1GET/api/open/v1/healthapplication/jsonTue, 29 Sep 2026 17:11:00 GMT
```

`POST /api/open/v1/users`（带 JSON body，示意）：

```
HanJiang-1POST/api/open/v1/usersapplication/jsonTue, 29 Sep 2026 17:12:00 GMTfc005f51a6e75586d2d5d078b657dxxx
```

### 3.5 验签时间窗

服务端校验 `X-App-Date` 与当前时间的差值，超过 **300 秒**（`OPENAPI_SIGNATURE_WINDOW_SECONDS`）即拒绝。客户端须保证系统时间与服务器同步（建议启用 NTP）。

## 4. 请求头说明

| 模式    | 请求头                   | 说明                                      |
| ----- | --------------------- | --------------------------------------- |
| plain | `X-App-Id`            | 应用 AppId                                |
| plain | `X-App-Key`           | 应用 AppKey（明文）                           |
| hmac  | `X-App-Id`            | 应用 AppId                                |
| hmac  | `X-App-Date`          | RFC1123 GMT 时间（参与签名）                    |
| hmac  | `X-App-Authorization` | 格式：`HanJiang-1 {app_id}:{signature}`    |
| 通用    | `Content-Type`        | 统一为 `application/json`（GET 无 body 也可携带） |

## 5. 示例 api（`/api/open/v1`）

| 方法  | 路径         | 说明                     | 所需 scope    |
| --- | ---------- | ---------------------- | ----------- |
| GET | `/health`  | 健康检查（凭证有效即可）           | 无           |
| GET | `/version` | 版本信息                   | 无           |
| GET | `/me`      | 当前应用信息                 | 无           |
| GET | `/ping`    | 连通性测试，返回应用身份与已授权 scope | `ping:read` |

> 以上为示例客户端演示的接口；其余业务端点（如用户管理）以服务端 Swagger（`/docs`）为准。

## 6. 示例 scope

| scope       | 含义    |
| ----------- | ----- |
| `ping:read` | 连通性测试 |

> 其余 scope 以服务端 Swagger（`/docs`）为准。

scope 通过管理端【开放应用 → 权限】勾选授权，修改后需服务端重启生效（启动时自动同步）；`X-App-Id` 校验通过后，接口层以 `require_app_scope(...)` 完成 scope 校验，无权调用返回 403。

## 7. Python 对接步骤

### 7.1 最小可用实现（约 30 行）

```python
import hashlib
import hmac
import json
from email.utils import formatdate

import requests

APP_ID = "hj_你的应用ID"
APP_KEY = "你的应用密钥"
BASE_URL = "http://127.0.0.1:8000/api/open/v1"
API_BASE_PATH = "/api/open/v1"  # 签名串 URI 前缀，含 /api/open/v1


def build_signing_string(method: str, uri: str, date: str, body: bytes = b"") -> str:
    """构造 HanJiang-1 待签名串：Ver + METHOD + URI + Content-Type + Date + SHA256(body)。

    date 必须与 X-App-Date 请求头为同一值（单点生成，避免跨秒不一致导致验签失败）。
    """
    body_hash = hashlib.sha256(body).hexdigest() if body else ""
    return "".join(["HanJiang-1", method.upper(), uri, "application/json", date, body_hash])


def call(method: str, path: str, body: dict | None = None) -> requests.Response:
    url = f"{BASE_URL}{path}"
    body_bytes = b""
    if body is not None:
        body_bytes = json.dumps(body).encode("utf-8")

    uri = f"{API_BASE_PATH}{path}"  # path 含 query 时原样拼接，如 "/users?page=1&page_size=5"
    date = formatdate(timeval=None, usegmt=True)  # RFC1123 GMT，单点生成
    signing_string = build_signing_string(method, uri, date, body_bytes)
    signature = hmac.new(APP_KEY.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = {
        "X-App-Id": APP_ID,
        "X-App-Date": date,
        "X-App-Authorization": f"HanJiang-1 {APP_ID}:{signature}",
        "Content-Type": "application/json",
    }
    return requests.request(method, url, headers=headers, data=body_bytes or None, timeout=10)


# GET 示例：探活四件套
for path in ("/health", "/version", "/ping", "/me"):
    resp = call("GET", path)
    print(path, "->", resp.status_code, resp.json())
```

### 7.2 完整演示客户端

`server/examples/openapi_client.py` 提供了生产级参考实现：支持 plain / hmac 双模式、凭证环境变量注入、`--verbose` 打印签名串、`--with-post` 全链路演示。用法：

```bash
python server/examples/openapi_client.py --verbose          # 展示签名串
OPENAPI_APP_ID=xxx OPENAPI_APP_KEY=xxx python server/examples/openapi_client.py
```

## 8. Go 对接步骤

参考实现（协议字段与服务端严格对齐；`query` 以原始字符串拼入 `path`，不做转义/排序）：

```go
package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const (
	appID           = "hj_你的应用ID"
	appKey          = "你的应用密钥"
	apiBasePath     = "/api/open/v1" // 签名串 URI 前缀
	baseURL         = "http://127.0.0.1:8000" + apiBasePath
	signContentType = "application/json"
)

// sign 计算 HanJiang-1 签名值（小写十六进制）
func sign(method, uri, date string, body []byte) string {
	bodyHash := ""
	if len(body) > 0 {
		sum := sha256.Sum256(body)
		bodyHash = hex.EncodeToString(sum[:])
	}
	signingString := "HanJiang-1" + method + uri + signContentType + date + bodyHash

	mac := hmac.New(sha256.New, []byte(appKey))
	mac.Write([]byte(signingString))
	return hex.EncodeToString(mac.Sum(nil))
}

// call 发送已签名请求；path 形如 "/users?page=1&page_size=5"（query 原样传入）
func call(method, path string, body []byte) (*http.Response, error) {
	uri := apiBasePath + path
	date := time.Now().UTC().Format(http.TimeFormat) // RFC1123 GMT
	auth := fmt.Sprintf("HanJiang-1 %s:%s", appID, sign(method, uri, date, body))

	req, err := http.NewRequest(method, baseURL+path, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-App-Id", appID)
	req.Header.Set("X-App-Date", date)
	req.Header.Set("X-App-Authorization", auth)
	req.Header.Set("Content-Type", signContentType)

	client := &http.Client{Timeout: 10 * time.Second}
	return client.Do(req)
}

func main() {
	// GET 示例：探活四件套
	for _, path := range []string{"/health", "/version", "/ping", "/me"} {
		resp, err := call(http.MethodGet, path, nil)
		if err != nil {
			panic(err)
		}
		data, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		fmt.Println(path, resp.StatusCode, string(data))
	}
}
```

> 提示：`http.TimeFormat` 输出即 RFC1123 GMT（如 `Tue, 30 Sep 2026 08:00:00 GMT`），与服务端 `formatdate(usegmt=True)` 一致。

## 9. 常见错误与排查

| 现象           | 可能原因                  | 排查动作                                                                                                                  |
| ------------ | --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `401 应用鉴权失败` | 凭证错误 / 时间窗超限 / 签名串不一致 | ① 核对 AppId、AppKey（含前后空格）；② 检查客户端与服务端时间差 ≤300s；③ 用 `--verbose` 模式核对签名串字段顺序与拼接值；④ 确认 Content-Type 固定 `application/json` |
| `403 无权限`    | scope 未授权或与接口要求不符     | 管理端为应用补授权 scope 并重启服务端                                                                                                |
| `422 参数校验失败` | 请求体不符合 Schema         | 按接口文档检查必填字段与格式                                                                                                        |
| `404 接口不存在`  | 路径或前缀错误               | 确认路径含 `/api/open/v1` 前缀                                                                                               |
| `500 服务内部错误` | 服务端异常                 | 查看服务端日志（含 request\_id 可快速定位）                                                                                          |

## 10. 安全建议

1. **AppKey 严格保密**：不写入前端、不提交到代码仓库，建议环境变量 / 密钥管理注入；
2. **优先使用 hmac 模式**：明文模式仅在可信内网使用；
3. **定期轮换 AppKey**：管理端支持密钥轮换，泄露后立即轮换；
4. **服务端时间校准**：启用 NTP，避免签名时间窗误判；
5. 所有开放接口的写操作（创建 / 更新 / 删除）均要求 `user:write` scope，最小权限原则授权。

