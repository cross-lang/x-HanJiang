<template>
  <div class="auth-page">
    <!-- 模块头 -->
    <div class="auth-head">
      <div class="auth-crumbs">认证和授权 / 通用参数</div>
      <h1 class="auth-title">通用参数</h1>
      <p class="auth-desc">
        开放接口调用涉及的公共请求头、凭证约定、统一响应结构与通用分页参数，全部接口通用。
      </p>
    </div>

    <!-- 公共请求头 -->
    <section class="auth-card">
      <h3 class="auth-card-title">公共请求头</h3>
      <p class="auth-lead">
        所有开放接口 <code>/api/open/v1</code> 请求均需携带应用凭证头（明文 / 签名模式取值不同）：
      </p>
      <el-table :data="headers" class="auth-table" row-key="name">
        <el-table-column prop="name" label="请求头" width="240">
          <template #default="{ row }">
            <code class="mono-cell">{{ row.name }}</code>
          </template>
        </el-table-column>
        <el-table-column label="必填" width="96">
          <template #default="{ row }">
            <span class="req-badge" :class="row.required ? 'req-yes' : 'req-maybe'">
              {{ row.required ? '必填' : '按模式' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="mode" label="适用模式" width="120">
          <template #default="{ row }">
            <span class="mode-badge" :class="`mode-${row.modeKey}`">{{ row.mode }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="desc" label="说明" />
      </el-table>
      <div class="auth-alert auth-alert-warn">
        <el-icon :size="15"><WarningFilled /></el-icon>
        <span>
          <b>AppKey 仅在创建应用或重置 Key 时明文返回一次</b>，请立即保存到安全位置；服务端只保存 SHA256 摘要（明文模式）与加密密文（签名模式），无法找回。
        </span>
      </div>
    </section>

    <!-- 凭证与调用约定 -->
    <section class="auth-card">
      <h3 class="auth-card-title">凭证与调用约定</h3>
      <div class="auth-algo">
        <div v-for="t in terms" :key="t.name" class="auth-algo-row">
          <span class="auth-algo-label">{{ t.name }}</span>
          <span class="auth-algo-value">{{ t.value }}</span>
        </div>
      </div>
    </section>

    <!-- 公共响应结构 -->
    <section class="auth-card">
      <h3 class="auth-card-title">公共响应结构</h3>
      <p class="auth-lead">
        所有接口统一返回如下 JSON 结构（成功与失败一致），HTTP 状态码与响应体 <code>code</code> 相同：
      </p>
      <CodeBlock :code="responseStructure" label="JSON" language="json" />
      <div style="margin-top: 16px">
        <el-table :data="responseFields" class="auth-table" row-key="field">
          <el-table-column prop="field" label="字段" width="140">
            <template #default="{ row }">
              <code class="mono-cell">{{ row.field }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <code>{{ row.type }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="desc" label="说明" />
        </el-table>
      </div>
    </section>

    <!-- 通用 Query 参数 -->
    <section class="auth-card">
      <h3 class="auth-card-title">通用 Query 参数</h3>
      <p class="auth-lead">列表类接口通用分页参数（具体以各接口文档为准）：</p>
      <el-table :data="queryParams" class="auth-table" row-key="name">
        <el-table-column prop="name" label="参数" width="140">
          <template #default="{ row }">
            <code class="mono-cell">{{ row.name }}</code>
          </template>
        </el-table-column>
        <el-table-column label="必填" width="96">
          <template #default="{ row }">
            <span class="req-badge" :class="row.required ? 'req-yes' : 'req-no'">
              {{ row.required ? '必填' : '可选' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <code>{{ row.type }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="desc" label="说明" />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import CodeBlock from './components/CodeBlock.vue'

const headers = [
  {
    name: 'X-App-Id',
    required: true,
    mode: '全部',
    modeKey: 'all',
    desc: '应用 ID（AppId），创建应用时生成，形如 hj_xxxxxxxx',
  },
  {
    name: 'X-App-Key',
    required: false,
    mode: 'plain',
    modeKey: 'plain',
    desc: '应用密钥（AppKey），明文模式下直接作为凭证携带',
  },
  {
    name: 'X-App-Date',
    required: false,
    mode: 'hmac',
    modeKey: 'hmac',
    desc: 'RFC1123 GMT 时间，参与签名计算，服务端校验 300 秒时间窗防重放',
  },
  {
    name: 'X-App-Authorization',
    required: false,
    mode: 'hmac',
    modeKey: 'hmac',
    desc: '签名凭证，格式：HanJiang-1 {app_id}:{signature}',
  },
  {
    name: 'Content-Type',
    required: true,
    mode: 'hmac',
    modeKey: 'hmac',
    desc: '固定 application/json（参与签名计算，GET 无 body 也需携带）',
  },
]

const terms = [
  { name: '调用前缀', value: '/api/open/v1（签名串中的 URI 必须包含此前缀）' },
  { name: 'AppId', value: '「应用管理 → 创建应用」时生成；创建后由管理端审批（pending → approved）' },
  { name: 'AppKey', value: '「应用管理 → 重置 Key」可重新生成；每次仅展示一次' },
  { name: 'scope 授权', value: '应用勾选所需 scope 提交申请，管理端审批通过后生效；未授权 scope 调用返回 403' },
  { name: '鉴权模式', value: 'plain / hmac / both，在创建应用时选择，可后续调整' },
  { name: '应用状态', value: '审批未通过（pending / rejected）或应用停用时，一律拒绝调用（403 / 401）' },
]

const responseStructure = `{
  "code": 200,              // HTTP 状态码（与 HTTP 状态一致）
  "message": "OK",          // 提示信息；失败时为错误原因
  "data": { ... },          // 业务数据；失败时可能携带 details 详情
  "timestamp": "2026-10-03T12:00:00Z",
  "request_id": "req_open_xxxxx"
}`

const responseFields = [
  { field: 'code', type: 'number', desc: 'HTTP 状态码，成功 200 / 创建 201，失败 4xx / 5xx' },
  { field: 'message', type: 'string', desc: '统一提示信息，成功为 OK，失败为错误原因' },
  { field: 'data', type: 'object', desc: '业务数据；校验类失败携带 { details: [...] } 详情' },
  { field: 'timestamp', type: 'string', desc: '响应时间（ISO8601 UTC）' },
  { field: 'request_id', type: 'string', desc: '请求追踪 ID，排查问题时提供给管理员' },
]

const queryParams = [
  { name: 'page', required: false, type: 'number', desc: '页码，默认 1' },
  { name: 'page_size', required: false, type: 'number', desc: '每页条数，默认 20' },
  { name: 'keyword', required: false, type: 'string', desc: '按名称/编码等模糊搜索（各接口定义不同）' },
  { name: 'status', required: false, type: 'string', desc: '状态过滤（各接口定义不同）' },
]
</script>

<style scoped>
@import '@/styles/auth-guide.css';

.req-badge {
  display: inline-block;
  min-width: 52px;
  text-align: center;
  font-size: 12px;
  line-height: 22px;
  border-radius: 11px;
  padding: 0 8px;
}
.req-yes {
  color: #f56c6c;
  background: #fef0f0;
}
.req-no {
  color: #909399;
  background: #f4f4f5;
}
.req-maybe {
  color: #e6a23c;
  background: #fdf6ec;
}
.mode-badge {
  display: inline-block;
  min-width: 52px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  line-height: 22px;
  border-radius: 4px;
  padding: 0 6px;
  white-space: nowrap;
}
.mode-all {
  color: #409eff;
  background: #ecf5ff;
}
.mode-hmac {
  color: #67c23a;
  background: #f0f9eb;
}
.mode-plain {
  color: #909399;
  background: #f4f4f5;
}
</style>
