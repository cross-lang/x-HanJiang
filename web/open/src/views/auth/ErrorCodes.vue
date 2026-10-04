<template>
  <div class="auth-page">
    <!-- 模块头 -->
    <div class="auth-head">
      <div class="auth-crumbs">认证和授权 / 通用错误码</div>
      <h1 class="auth-title">通用错误码</h1>
      <p class="auth-desc">
        开放接口统一返回 <code>{code, message, data, timestamp, request_id}</code> 结构，<code>code</code> 与 HTTP 状态码一致。以下为常见状态码与处理建议。
      </p>
    </div>

    <!-- 常用错误码 -->
    <section class="auth-card">
      <h3 class="auth-card-title">常用错误码</h3>
      <el-table :data="errorCodes" class="auth-table" row-key="code">
        <el-table-column label="HTTP 状态码" width="130">
          <template #default="{ row }">
            <span class="auth-code-badge" :class="codeClass(row.code)">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="scenario" label="典型场景" width="230" />
        <el-table-column prop="message" label="错误信息示例" />
        <el-table-column prop="suggestion" label="处理建议" />
      </el-table>
    </section>

    <!-- 网关鉴权错误 -->
    <section class="auth-card">
      <h3 class="auth-card-title">网关鉴权错误（401 / 403）</h3>
      <p class="auth-lead">
        开放接口网关按序执行：凭证有效性 → 审批门槛 → 模式分流 → scope 授权，错误信息与真实后端一致：
      </p>
      <el-table :data="gatewayErrors" class="auth-table" row-key="message">
        <el-table-column label="状态码" width="100">
          <template #default="{ row }">
            <span class="auth-code-badge" :class="codeClass(row.code)">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="错误信息" width="400">
          <template #default="{ row }">
            <code class="mono-cell">{{ row.message }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="cause" label="原因 / 处理建议" />
      </el-table>
    </section>

    <!-- 排查指引 -->
    <section class="auth-card">
      <h3 class="auth-card-title">401 鉴权失败排查指引</h3>
      <ol class="auth-steps">
        <li><b>AppId / AppKey</b> 是否正确（含前后空格）；</li>
        <li>本机系统时间是否与服务器同步（签名时间窗 300 秒）；</li>
        <li>签名协议是否与服务端一致（<code>Content-Type</code> 固定 <code>application/json</code>、URI 含 <code>/api/open/v1</code> 前缀、Date 为 RFC1123 GMT）；</li>
        <li>应用 <code>auth_mode</code> 是否与客户端一致（plain / hmac）。</li>
      </ol>
    </section>

    <!-- 错误响应示例 -->
    <section class="auth-card">
      <h3 class="auth-card-title">错误响应示例</h3>
      <CodeBlock :code="errorExample" label="JSON" />
    </section>
  </div>
</template>

<script setup lang="ts">
import CodeBlock from './components/CodeBlock.vue'

const errorCodes = [
  { code: 400, scenario: '请求语法错误 / 业务校验失败', message: '请求参数不合法', suggestion: '检查请求参数与接口文档' },
  { code: 401, scenario: '凭证缺失 / 无效 / 签名校验失败', message: '应用鉴权失败 / 缺少请求头 X-App-Id', suggestion: '核对 AppId / AppKey、时间同步、签名协议（见下方排查指引）' },
  { code: 403, scenario: '应用未审批 / scope 未授权', message: '应用 hj_xxx 未通过审批… / 应用缺少 scope: user:read', suggestion: '管理端审批应用；在应用管理补充申请所需 scope' },
  { code: 404, scenario: '资源不存在', message: '用户 99 不存在', suggestion: '核对路径参数 ID' },
  { code: 409, scenario: '唯一约束冲突', message: '用户名 demo 已存在 / 角色编码 role_x 已存在', suggestion: '换用未占用名称 / 编码' },
  { code: 422, scenario: '参数校验失败（Pydantic）', message: 'Validation error（data.details 含字段级错误）', suggestion: '按 details 修正请求体字段' },
  { code: 429, scenario: '触发限流（预留）', message: 'Too Many Requests', suggestion: '降低调用频率，按 X-RateLimit-* 响应头退避' },
  { code: 500, scenario: '服务端未处理异常', message: 'Internal server error', suggestion: '携带 request_id 联系平台管理员' },
  { code: 502, scenario: '外部服务调用失败', message: 'External service error', suggestion: '稍后重试；持续失败携带 request_id 反馈' },
]

const gatewayErrors = [
  {
    code: 401,
    message: '缺少请求头 X-App-Id',
    cause: '请求未携带应用凭证头；检查请求头命名与大小写',
  },
  {
    code: 401,
    message: 'App 无效或已停用',
    cause: 'AppId 不存在，或应用状态非 active；在管理端检查应用状态',
  },
  {
    code: 403,
    message: '应用 {app_id} 未通过审批（当前状态：pending / rejected），请联系管理员',
    cause: '开发者自助申请的应用须管理端审批通过（approval_status = approved）方可调用',
  },
  {
    code: 401,
    message: '应用鉴权失败',
    cause: '明文 Key 与摘要不匹配，或 HMAC 签名重算不一致（协议/时间/密钥问题，见排查指引）',
  },
  {
    code: 403,
    message: '应用缺少 scope: {scope_code}',
    cause: '接口需要对应 scope，应用未申请或未审批通过；在应用管理提交 scope 申请',
  },
]

const errorExample = `// 403 未审批 / scope 不足
{
  "code": 403,
  "message": "应用缺少 scope: user:read",
  "data": null,
  "timestamp": "2026-10-03T12:00:00Z",
  "request_id": "req_open_xxxxx"
}

// 422 参数校验失败（data.details 携带字段级错误）
{
  "code": 422,
  "message": "Validation error",
  "data": {
    "details": [
      { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error" }
    ]
  },
  "timestamp": "2026-10-03T12:00:00Z",
  "request_id": "req_open_xxxxx"
}`

function codeClass(code: number): string {
  if (code < 400) return 'code-2xx'
  if (code < 500) return 'code-4xx'
  return 'code-5xx'
}
</script>

<style scoped>
@import '@/styles/auth-guide.css';
</style>
