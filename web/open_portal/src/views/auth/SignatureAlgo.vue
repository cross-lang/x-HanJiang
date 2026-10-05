<template>
  <div class="auth-page">
    <!-- 模块头 -->
    <PageHead
      crumbs="认证和授权 / 签名算法"
      title="签名算法 HanJiang-1"
      desc="hmac 模式采用 HanJiang-1 签名协议：拼接固定签名串后以 AppKey 计算 HMAC-SHA256，输出十六进制小写签名。全程无分隔符、无随机因子，服务端在 300 秒时间窗内校验。"
    />

    <AuthAnchorNav :anchors="anchors" />

    <!-- 签名公式：分步可视化 -->
    <section id="formula" class="auth-card">
      <h3 class="auth-card-title">签名公式</h3>
      <p class="auth-lead">签名串由 6 段固定拼接（无分隔符），再经 HMAC-SHA256 得到签名值：</p>

      <div class="sig-flow">
        <div class="sig-seg sig-alg">HanJiang-1</div>
        <div class="sig-plus">+</div>
        <div class="sig-seg">METHOD</div>
        <div class="sig-plus">+</div>
        <div class="sig-seg">URI</div>
        <div class="sig-plus">+</div>
        <div class="sig-seg">Content-Type</div>
        <div class="sig-plus">+</div>
        <div class="sig-seg">Date</div>
        <div class="sig-plus">+</div>
        <div class="sig-seg sig-hash">SHA256(body)</div>
      </div>
      <div class="sig-result">
        <span>签名值</span>
        <code>= HMAC-SHA256(AppKey, 签名串) → 十六进制小写</code>
      </div>
    </section>

    <!-- 参数说明 -->
    <section id="segments" class="auth-card">
      <h3 class="auth-card-title">签名串各段说明</h3>
      <div class="auth-algo">
        <div class="auth-algo-row">
          <span class="auth-algo-label">签名串</span>
          <span class="auth-algo-value"><code>HanJiang-1 + METHOD + URI + Content-Type + Date + SHA256(body)</code>，各段直接拼接无分隔符</span>
        </div>
        <div class="auth-algo-row">
          <span class="auth-algo-label">签名值</span>
          <span class="auth-algo-value">以 <b>AppKey</b> 为密钥计算 <code>HMAC-SHA256</code>，输出十六进制小写</span>
        </div>
        <div class="auth-algo-row">
          <span class="auth-algo-label">URI</span>
          <span class="auth-algo-value">完整路径 + 查询串（不含域名），必须包含 <code>/api/open/v1</code> 前缀</span>
        </div>
        <div class="auth-algo-row">
          <span class="auth-algo-label">Content-Type</span>
          <span class="auth-algo-value">固定 <code>application/json</code>，与请求是否携带 body 无关</span>
        </div>
        <div class="auth-algo-row">
          <span class="auth-algo-label">Date</span>
          <span class="auth-algo-value">RFC1123 GMT 格式（如 <code>Sat, 03 Oct 2026 12:00:00 GMT</code>），经 <code>X-App-Date</code> 请求头传递</span>
        </div>
        <div class="auth-algo-row">
          <span class="auth-algo-label">空 body</span>
          <span class="auth-algo-value">GET 等无请求体时，<code>SHA256(body)</code> 部分取空字符串</span>
        </div>
        <div class="auth-algo-row">
          <span class="auth-algo-label">防重放</span>
          <span class="auth-algo-value">服务端校验 <code>X-App-Date</code> 与服务器时间差在 300 秒内，超出即拒绝</span>
        </div>
      </div>
    </section>

    <!-- 签名步骤 -->
    <section id="steps" class="auth-card">
      <h3 class="auth-card-title">签名步骤</h3>
      <ol class="auth-steps">
        <li>生成 RFC1123 GMT 格式的当前时间 <code>date</code>（与请求头 <code>X-App-Date</code> 必须是同一个值，单点生成）；</li>
        <li>构造 URI：接口路径 + 查询串（如 <code>/api/open/v1/users?page=1</code>，不含域名）；</li>
        <li>有请求体时计算 <code>SHA256(body)</code>（body 为 UTF-8 JSON 字节流），无请求体取空字符串；</li>
        <li>按上述公式拼接待签名串，以 <b>AppKey</b> 为密钥计算 <code>HMAC-SHA256</code>，得十六进制签名 <code>signature</code>；</li>
        <li>请求头携带 <code>X-App-Id</code>、<code>X-App-Date</code>、<code>X-App-Authorization: HanJiang-1 {app_id}:{signature}</code>，并固定携带 <code>Content-Type: application/json</code>；</li>
        <li>服务端校验签名与时间窗后放行；scope 未授权或应用未审批将返回 403。</li>
      </ol>
    </section>

    <!-- 代码示例 -->
    <section id="examples" class="auth-card">
      <h3 class="auth-card-title">代码示例</h3>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="Python" name="python">
          <p class="auth-note">
            完整可运行客户端见仓库 <code>server/examples/openapi_client.py</code>（支持 plain / hmac，GET / POST / DELETE 全链路演示）。以下为最简 GET + POST 签名实现：
          </p>
          <CodeBlock :code="pythonCode" label="Python" language="python" />
        </el-tab-pane>
        <el-tab-pane label="Go" name="go">
          <p class="auth-note">仅依赖 Go 标准库（crypto/hmac、crypto/sha256、net/http、time）：</p>
          <CodeBlock :code="goCode" label="Go" language="go" />
        </el-tab-pane>
      </el-tabs>
    </section>

    <!-- curl 调试示例 -->
    <section id="curl" class="auth-card">
      <h3 class="auth-card-title">curl 调试示例</h3>
      <p class="auth-lead">
        调试阶段可在开放平台「应用管理 → 重置 Key」后使用明文模式快速验证；签名模式下需先按上述算法生成 <code>X-App-Authorization</code>：
      </p>
      <CodeBlock :code="curlCode" label="cURL" language="bash" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import CodeBlock from '@/components/CodeBlock.vue'
import PageHead from '@/components/PageHead.vue'
import AuthAnchorNav from '@/components/AuthAnchorNav.vue'

const activeTab = ref('python')

const anchors = [
  { id: 'formula', label: '签名公式' },
  { id: 'segments', label: '各段说明' },
  { id: 'steps', label: '签名步骤' },
  { id: 'examples', label: '代码示例' },
  { id: 'curl', label: 'curl 调试' },
]

const pythonCode = `import hashlib, hmac, json, time
from email.utils import formatdate
import requests

ALGORITHM = "HanJiang-1"
CONTENT_TYPE = "application/json"
BASE = "http://127.0.0.1:8000/api/open/v1"

APP_ID = "hj_xxxxxxxx"      # 开放平台应用管理 → 应用详情
APP_KEY = "your-app-key"    # 创建应用 / 重置 Key 时仅返回一次

def build_signing_string(method, uri, date, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest() if body else ""
    return "".join([ALGORITHM, method.upper(), uri, CONTENT_TYPE, date, body_hash])

def request(method, path, body=None):
    body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else b""
    uri = f"/api/open/v1{path}"                      # 含版本前缀，不含域名
    date = formatdate(timeval=None, usegmt=True)     # RFC1123 GMT，签名串与请求头同值
    signing_string = build_signing_string(method, uri, date, body_bytes)
    signature = hmac.new(APP_KEY.encode(), signing_string.encode(), hashlib.sha256).hexdigest()
    headers = {
        "X-App-Id": APP_ID,
        "X-App-Date": date,
        "X-App-Authorization": f"{ALGORITHM} {APP_ID}:{signature}",
        "Content-Type": CONTENT_TYPE,                # GET 无 body 也固定携带
    }
    return requests.request(method, BASE + path, headers=headers,
                            data=body_bytes or None, timeout=10)

# GET（无 body 签名）
resp = request("GET", "/health")
print(resp.status_code, resp.json())

# POST（带 body 签名）
resp = request("POST", "/users", body={"username": "demo", "name": "演示"})
print(resp.status_code, resp.json())`

const goCode = `package main

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
    algorithm    = "HanJiang-1"
    contentType  = "application/json"
    apiBasePath  = "/api/open/v1"
    hdrAppID     = "X-App-Id"
    hdrDate      = "X-App-Date"
    hdrSignature = "X-App-Authorization"
)

func sha256Hex(s string) string {
    sum := sha256.Sum256([]byte(s))
    return hex.EncodeToString(sum[:])
}

func hmacSHA256Hex(key, data string) string {
    mac := hmac.New(sha256.New, []byte(key))
    mac.Write([]byte(data))
    return hex.EncodeToString(mac.Sum(nil))
}

// buildSigningString: HanJiang-1 + METHOD + URI + Content-Type + Date + SHA256(body)
func buildSigningString(method, uri, date string, body []byte) string {
    bodyHash := ""
    if len(body) > 0 {
        bodyHash = sha256Hex(string(body))
    }
    return algorithm + strings.ToUpper(method) + uri + contentType + date + bodyHash
}

func signedRequest(method, path string, body []byte) (*http.Response, error) {
    uri := apiBasePath + path
    date := time.Now().UTC().Format(http.TimeFormat) // RFC1123 GMT
    signature := hmacSHA256Hex(appKey, buildSigningString(method, uri, date, body))

    req, err := http.NewRequest(method, "http://127.0.0.1:8000"+uri, bytes.NewReader(body))
    if err != nil {
        return nil, err
    }
    req.Header.Set(hdrAppID, appID)
    req.Header.Set(hdrDate, date)
    req.Header.Set(hdrSignature, algorithm+" "+appID+":"+signature)
    req.Header.Set("Content-Type", contentType) // GET 无 body 也固定携带
    return http.DefaultClient.Do(req)
}

var (
    appID  = "hj_xxxxxxxx"   // 开放平台应用管理 → 应用详情
    appKey = "your-app-key"  // 创建应用 / 重置 Key 时仅返回一次
)

func main() {
    // GET（无 body 签名）
    resp, err := signedRequest("GET", "/health", nil)
    if err != nil {
        panic(err)
    }
    data, _ := io.ReadAll(resp.Body)
    resp.Body.Close()
    fmt.Printf("GET /health status=%d body=%s\\n", resp.StatusCode, data)

    // POST（带 body 签名）
    body := []byte(\`{"username":"demo","name":"演示"}\`)
    resp, err = signedRequest("POST", "/users", body)
    if err != nil {
        panic(err)
    }
    data, _ = io.ReadAll(resp.Body)
    resp.Body.Close()
    fmt.Printf("POST /users status=%d body=%s\\n", resp.StatusCode, data)
}`

const curlCode = `# 明文模式（调试）：仅需 X-App-Id / X-App-Key
curl -X GET "http://127.0.0.1:8000/api/open/v1/health" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Key: your-app-key"

# hmac 签名模式：X-App-Date 必须与签名串中 Date 完全一致（RFC1123 GMT）
curl -X POST "http://127.0.0.1:8000/api/open/v1/users" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:<signature>" \\
  -H "Content-Type: application/json" \\
  -d '{"username":"demo","name":"演示"}'`
</script>

<style scoped>
@import '@/styles/auth-guide.css';

/* ─── 签名公式分步可视化 ─── */
.sig-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px 12px;
  background: linear-gradient(135deg, var(--hj-primary-bg) 0%, #f5faff 100%);
  border: 1px solid var(--hj-primary-border);
  border-radius: var(--hj-radius-md);
}
.sig-seg {
  padding: 7px 14px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--hj-primary-border);
  color: var(--hj-text-title);
  font-family: var(--hj-font-mono);
  font-size: 12.5px;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.08);
  white-space: nowrap;
}
.sig-alg {
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  border: none;
  color: #fff;
}
.sig-hash {
  background: #eef4ff;
}
.sig-plus {
  color: var(--hj-text-muted);
  font-size: 13px;
  font-weight: 700;
}
.sig-result {
  margin-top: 14px;
  padding: 12px 18px;
  border: 1px dashed var(--hj-primary-border);
  border-radius: 8px;
  background: var(--hj-bg-card);
  text-align: center;
  font-size: 13.5px;
  color: var(--hj-text-regular);
}
.sig-result span {
  font-weight: 600;
  color: var(--hj-text-title);
  margin-right: 8px;
}
.sig-result code {
  font-family: var(--hj-font-mono);
  font-size: 12.5px;
  color: var(--hj-primary);
  word-break: break-all;
}
</style>
