<template>
  <div class="guide-page">
    <!-- 公共请求头 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="guide-title">公共请求头</h3>
      <p class="guide-lead">
        所有开放接口 <code>/api/open/v1</code> 请求均需携带应用凭证头（明文 / 签名模式取值不同）：
      </p>
      <el-table :data="headers" border size="small">
        <el-table-column prop="name" label="请求头" width="220" />
        <el-table-column prop="required" label="必填" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.required" size="small" type="danger">必填</el-tag>
            <el-tag v-else size="small" type="info">按模式</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mode" label="适用模式" width="110" />
        <el-table-column prop="desc" label="说明" />
      </el-table>
      <el-alert type="warning" :closable="false" class="hj-mt-12">
        <b>AppKey 仅在创建应用或重置 Key 时明文返回一次</b>，请立即保存到安全位置；服务端只保存
        SHA256 摘要（明文模式）与加密密文（签名模式），无法找回。
      </el-alert>
    </el-card>

    <!-- 凭证与调用约定 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="guide-title">凭证与调用约定</h3>
      <el-table :data="terms" border size="small">
        <el-table-column prop="name" label="项目" width="150" />
        <el-table-column prop="value" label="约定" />
      </el-table>
    </el-card>

    <!-- 公共响应结构 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="guide-title">公共响应结构</h3>
      <p class="guide-lead">
        所有接口统一返回如下 JSON 结构（成功与失败一致），HTTP 状态码与响应体 <code>code</code> 相同：
      </p>
      <pre class="code-block">{{ responseStructure }}</pre>
      <el-table :data="responseFields" border size="small" class="hj-mt-12">
        <el-table-column prop="field" label="字段" width="120" />
        <el-table-column prop="type" label="类型" width="90" />
        <el-table-column prop="desc" label="说明" />
      </el-table>
    </el-card>

    <!-- 通用 Query 参数 -->
    <el-card shadow="never">
      <h3 class="guide-title">通用 Query 参数</h3>
      <p class="guide-lead">列表类接口通用分页参数（具体以各接口文档为准）：</p>
      <el-table :data="queryParams" border size="small">
        <el-table-column prop="name" label="参数" width="140" />
        <el-table-column prop="required" label="必填" width="80">
          <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="90" />
        <el-table-column prop="desc" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
const headers = [
  {
    name: 'X-App-Id',
    required: true,
    mode: '全部',
    desc: '应用 ID（AppId），创建应用时生成，形如 hj_xxxxxxxx',
  },
  {
    name: 'X-App-Key',
    required: false,
    mode: 'plain',
    desc: '应用密钥（AppKey），明文模式下直接作为凭证携带',
  },
  {
    name: 'X-App-Date',
    required: false,
    mode: 'hmac',
    desc: 'RFC1123 GMT 时间，参与签名计算，服务端校验 300 秒时间窗防重放',
  },
  {
    name: 'X-App-Authorization',
    required: false,
    mode: 'hmac',
    desc: '签名凭证，格式：HanJiang-1 {app_id}:{signature}',
  },
  {
    name: 'Content-Type',
    required: true,
    mode: 'hmac',
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
.guide-lead code {
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.hj-mb-20 {
  margin-bottom: 20px;
}
.hj-mt-12 {
  margin-top: 12px;
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
