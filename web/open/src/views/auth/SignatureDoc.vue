<template>
  <div class="guide-page">
    <!-- 鉴权模式总览 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="guide-title">鉴权模式</h3>
      <p class="guide-lead">
        开放接口 <code>/api/open/v1</code> 面向外部应用，与开放平台门户自身的会话登录（JWT + Redis
        登录态）完全隔离。调用方应用在管理端审批通过后，凭应用凭证调用：
      </p>
      <el-table :data="authModes" border size="small">
        <el-table-column prop="mode" label="模式" width="90" />
        <el-table-column prop="credential" label="凭证方式" />
        <el-table-column prop="scenario" label="适用场景" />
      </el-table>
      <el-alert type="info" :closable="false" class="hj-mt-12">
        生产对接推荐 <b>hmac</b> 签名模式：明文模式下 AppKey 在请求头中直接暴露，仅建议在可信内网使用。
      </el-alert>
    </el-card>

    <!-- 签名算法 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="guide-title">HanJiang-1 签名算法</h3>
      <el-descriptions :column="1" border class="hj-mb-16">
        <el-descriptions-item label="签名串">
          <code class="formula">HanJiang-1 + METHOD + URI + Content-Type + Date + SHA256(body)</code>
          <span class="formula-note">（各段直接拼接，无分隔符）</span>
        </el-descriptions-item>
        <el-descriptions-item label="签名值">HMAC-SHA256(AppKey, 签名串)，输出十六进制小写</el-descriptions-item>
        <el-descriptions-item label="URI">完整路径 + 查询串（不含域名），必须包含 <code>/api/open/v1</code> 前缀</el-descriptions-item>
        <el-descriptions-item label="Content-Type">固定 <code>application/json</code>，与请求是否携带 body 无关</el-descriptions-item>
        <el-descriptions-item label="Date">RFC1123 GMT 格式（如 <code>Sat, 03 Oct 2026 12:00:00 GMT</code>），经 <code>X-App-Date</code> 请求头传递</el-descriptions-item>
        <el-descriptions-item label="空 body">GET 等无请求体时，SHA256(body) 部分取空字符串</el-descriptions-item>
        <el-descriptions-item label="防重放">服务端校验 <code>X-App-Date</code> 与服务器时间差在 300 秒内，超出即拒绝</el-descriptions-item>
      </el-descriptions>

      <div class="sign-box">
        <div class="sign-title">签名步骤</div>
        <ol class="sign-steps">
          <li>生成 RFC1123 GMT 格式的当前时间 <code>date</code>（与请求头 <code>X-App-Date</code> 必须是同一个值，单点生成）；</li>
          <li>构造 URI：接口路径 + 查询串（如 <code>/api/open/v1/users?page=1</code>，不含域名）；</li>
          <li>有请求体时计算 <code>SHA256(body)</code>（body 为 UTF-8 JSON 字节流），无请求体取空字符串；</li>
          <li>按上述公式拼接待签名串，以 <b>AppKey</b> 为密钥计算 <code>HMAC-SHA256</code>，得十六进制签名 <code>signature</code>；</li>
          <li>请求头携带 <code>X-App-Id</code>、<code>X-App-Date</code>、<code>X-App-Authorization: HanJiang-1 {app_id}:{signature}</code>，并固定携带 <code>Content-Type: application/json</code>；</li>
          <li>服务端校验签名与时间窗后放行；scope 未授权或应用未审批将返回 403。</li>
        </ol>
      </div>
    </el-card>

    <!-- 代码示例 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="guide-title">代码示例</h3>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="Python" name="python">
          <p class="tab-note">
            完整可运行客户端见仓库 <code>server/examples/openapi_client.py</code>（支持 plain / hmac，
            GET / POST / DELETE 全链路演示）。以下为最简 GET + POST 签名实现：
          </p>
          <pre class="code-block">{{ pythonCode }}</pre>
        </el-tab-pane>
        <el-tab-pane label="Go" name="go">
          <p class="tab-note">仅依赖 Go 标准库（crypto/hmac、crypto/sha256、net/http、time）：</p>
          <pre class="code-block">{{ goCode }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- curl 示例 -->
    <el-card shadow="never">
      <h3 class="guide-title">curl 调试示例</h3>
      <p class="guide-lead">
        调试阶段可在开放平台「应用管理 → 重置 Key」后使用明文模式快速验证；签名模式下需先按上述算法
        生成 <code>X-App-Authorization</code>：
      </p>
      <pre class="code-block">{{ curlCode }}</pre>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('python')

const authModes = [
  { mode: 'plain', credential: '请求头直接携带 X-App-Id + X-App-Key（明文）', scenario: '可信内网 / 联调调试' },
  { mode: 'hmac', credential: 'X-App-Id + X-App-Date + X-App-Authorization（HanJiang-1 签名）', scenario: '生产环境（推荐）' },
  { mode: 'both', credential: '两种凭证均接受', scenario: '灰度迁移期' },
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
.guide-page {
  max-width: 1080px;
  margin: 0 auto;
}
.guide-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.guide-lead {
  margin: 0 0 12px;
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}
.guide-lead code,
.tab-note code {
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.hj-mb-20 {
  margin-bottom: 20px;
}
.hj-mb-16 {
  margin-bottom: 16px;
}
.hj-mt-12 {
  margin-top: 12px;
}
.formula {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
}
.formula-note {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
.sign-box {
  margin-top: 8px;
  border: 1px solid #eceef3;
  border-radius: 10px;
  padding: 14px 18px;
  background: #fafbfd;
}
.sign-title {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 8px;
}
.sign-steps {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #606266;
  line-height: 1.9;
}
.sign-steps code {
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.tab-note {
  margin: 0 0 12px;
  font-size: 13px;
  color: #909399;
  line-height: 1.7;
}
.code-block {
  margin: 0;
  padding: 14px 16px;
  border-radius: 8px;
  background: #f6f8fa;
  font-size: 12px;
  line-height: 1.7;
  overflow-x: auto;
  user-select: text;
  white-space: pre;
}
</style>
