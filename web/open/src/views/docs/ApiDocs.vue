<template>
  <div class="docs-page">
    <!-- 鉴权与签名说明 -->
    <el-card shadow="never" class="hj-mb-20">
      <h3 class="docs-title">调用说明</h3>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="调用前缀">/api/open/v1</el-descriptions-item>
        <el-descriptions-item label="凭证">X-App-Id（应用 ID）+ X-App-Key（应用密钥）</el-descriptions-item>
        <el-descriptions-item label="鉴权方式">
          <el-tag size="small" type="warning" class="hj-mr-8">明文</el-tag>
          请求头直接携带 AppKey；或
          <el-tag size="small" type="success" class="hj-ml-8">HMAC 签名</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="权限控制">接口按 scope 授权，未申请/未审批通过的 scope 调用将返回 403</el-descriptions-item>
      </el-descriptions>

      <div class="sign-box">
        <div class="sign-title">HMAC 签名流程（摘要）</div>
        <ol class="sign-steps">
          <li>生成时间戳 <code>timestamp</code>（毫秒）与随机串 <code>nonce</code>；</li>
          <li>按规则拼接规范化请求串（方法 + 路径 + 查询参数 + 请求体摘要）；</li>
          <li>以 <code>AppKey</code> 为密钥计算 <code>HMAC-SHA256</code> 得到 <code>signature</code>；</li>
          <li>请求头携带 <code>X-App-Id</code>、<code>X-Timestamp</code>、<code>X-Nonce</code>、<code>X-Signature</code>；</li>
          <li>服务端校验签名与时间窗（防重放）。</li>
        </ol>
        <div class="sign-note">签名规范以开放平台正式文档为准（当前为能力演示阶段，后端签名中间件待完善）。</div>
      </div>
    </el-card>

    <!-- 接口目录（按模块分组） -->
    <div v-for="module in modules" :key="module.name" class="hj-mb-20">
      <h3 class="module-title">{{ module.name }}</h3>
      <el-card v-for="api in module.items" :key="api.id" shadow="never" class="api-card">
        <div class="api-header">
          <el-tag :type="methodTagType(api.method)" size="small" class="method-tag">{{ api.method }}</el-tag>
          <code class="api-path">{{ api.path }}</code>
          <el-tag v-if="api.scope" size="small" class="hj-ml-8">{{ api.scope }}</el-tag>
          <el-tag v-else size="small" type="info" class="hj-ml-8">无需 scope</el-tag>
          <span class="api-name">{{ api.name }}</span>
        </div>
        <p class="api-desc">{{ api.description }}</p>

        <el-collapse>
          <el-collapse-item title="入参" name="params">
            <el-table :data="api.params" border size="small">
              <el-table-column prop="name" label="参数" width="180" />
              <el-table-column prop="location" label="位置" width="90" />
              <el-table-column prop="required" label="必填" width="70">
                <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
              </el-table-column>
              <el-table-column prop="type" label="类型" width="100" />
              <el-table-column prop="description" label="说明" />
            </el-table>
            <div v-if="api.params.length === 0" class="empty-note">无入参</div>
          </el-collapse-item>
          <el-collapse-item title="返参示例" name="response">
            <pre class="code-block">{{ api.response_example }}</pre>
            <div class="resp-desc">{{ api.response_desc }}</div>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </div>

    <el-alert type="info" :closable="false" class="hj-mb-20">
      当前为内置静态目录（与本仓库 server/src/api/open/v1 的既有接口一一对应）。待后端提供统一文档接口
      <code>GET /docs/catalog</code> 后，本页将自动切换为动态数据源。
    </el-alert>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ApiDocEndpoint } from '@/types/apiDoc'

/** 内置静态接口目录：与 server/src/api/open/v1 既有接口一一对应 */
const STATIC_DOCS: ApiDocEndpoint[] = [
  // ── 健康管理 ──
  {
    id: 'health',
    module: '健康管理',
    name: '开放平台健康检查',
    path: '/health',
    method: 'GET',
    auth_mode: 'app-key',
    scope: '',
    description: '轻量探活，确认开放平台网关正常且调用方凭证有效。',
    params: [],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: { status: 'ok', service: 'openapi', app: 'hanjiang' },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '凭证有效时返回 ok 状态与服务标识。',
  },
  {
    id: 'version',
    module: '健康管理',
    name: '开放平台版本信息',
    path: '/version',
    method: 'GET',
    auth_mode: 'app-key',
    scope: '',
    description: '返回开放平台 API 版本号。',
    params: [],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: { app_version: '0.1.0', api_version: 'v1' },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '应用版本与 API 版本。',
  },
  // ── 应用信息 ──
  {
    id: 'me',
    module: '应用信息',
    name: '当前开放平台应用信息',
    path: '/me',
    method: 'GET',
    auth_mode: 'app-key',
    scope: '',
    description: '返回当前调用方应用信息（App ID、名称、鉴权模式、已授权 scope 等）。',
    params: [],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: {
          id: 1,
          app_id: 'hj_app_xxxx',
          name: '我的应用',
          auth_mode: 'hmac',
          scopes: ['user:read'],
          status: 'active',
        },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '应用详情（AppKey 明文不会在此返回）。',
  },
  // ── 用户管理 ──
  {
    id: 'user-create',
    module: '用户管理',
    name: '创建用户',
    path: '/users',
    method: 'POST',
    auth_mode: 'app-key',
    scope: 'user:write',
    description: '创建用户（校验邮箱/用户名全局唯一），需 user:write scope。',
    params: [
      { name: 'username', location: 'body', required: true, type: 'string', description: '用户名（3-50 位）' },
      { name: 'email', location: 'body', required: true, type: 'string', description: '邮箱（全局唯一）' },
      { name: 'password', location: 'body', required: true, type: 'string', description: '初始密码（8-64 位）' },
      { name: 'name', location: 'body', required: true, type: 'string', description: '姓名' },
      { name: 'phone', location: 'body', required: true, type: 'string', description: '手机号' },
      { name: 'gender', location: 'body', required: true, type: 'string', description: '性别（male/female）' },
      { name: 'birthday', location: 'body', required: true, type: 'string', description: '生日（YYYY-MM-DD）' },
      { name: 'role_ids', location: 'body', required: true, type: 'number[]', description: '角色 ID 列表（至少 1 个）' },
      { name: 'status', location: 'body', required: false, type: 'string', description: '状态（enabled/disabled，默认 enabled）' },
    ],
    response_example: JSON.stringify(
      {
        code: 201,
        message: 'OK',
        data: {
          id: 3,
          username: 'dev_user',
          email: 'dev@example.com',
          name: '开发者',
          roles: [{ id: 3, role_name: '普通用户', role_code: 'user' }],
          status: 'enabled',
        },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '创建成功的用户信息（不含密码哈希）。',
  },
  {
    id: 'user-list',
    module: '用户管理',
    name: '用户列表',
    path: '/users',
    method: 'GET',
    auth_mode: 'app-key',
    scope: 'user:read',
    description: '分页查询用户列表，支持关键字/状态过滤，需 user:read scope。',
    params: [
      { name: 'page', location: 'query', required: false, type: 'number', description: '页码（默认 1）' },
      { name: 'page_size', location: 'query', required: false, type: 'number', description: '每页条数（默认 20）' },
      { name: 'keyword', location: 'query', required: false, type: 'string', description: '按用户名/邮箱/姓名模糊搜索' },
      { name: 'status', location: 'query', required: false, type: 'string', description: '状态过滤（enabled/disabled）' },
    ],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: {
          items: [
            { id: 1, username: 'superadmin', name: '超级管理员', roles: [], status: 'enabled' },
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '分页结构 {items, total, page, page_size, total_pages}。',
  },
  {
    id: 'user-get',
    module: '用户管理',
    name: '用户详情',
    path: '/users/{user_id}',
    method: 'GET',
    auth_mode: 'app-key',
    scope: 'user:read',
    description: '查询单个用户详情，需 user:read scope。',
    params: [{ name: 'user_id', location: 'path', required: true, type: 'number', description: '用户 ID' }],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: { id: 2, username: 'yangzhuang', name: '杨壮', status: 'enabled' },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '用户详情；不存在时返回 404。',
  },
  {
    id: 'user-update',
    module: '用户管理',
    name: '更新用户',
    path: '/users/{user_id}',
    method: 'PATCH',
    auth_mode: 'app-key',
    scope: 'user:write',
    description: '更新用户信息（仅更新提供的字段），需 user:write scope。',
    params: [
      { name: 'user_id', location: 'path', required: true, type: 'number', description: '用户 ID' },
      { name: 'name', location: 'body', required: false, type: 'string', description: '姓名' },
      { name: 'phone', location: 'body', required: false, type: 'string', description: '手机号' },
      { name: 'status', location: 'body', required: false, type: 'string', description: '状态（enabled/disabled）' },
    ],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: { id: 2, username: 'yangzhuang', name: '杨壮', status: 'disabled' },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '更新后的用户信息。',
  },
  {
    id: 'user-delete',
    module: '用户管理',
    name: '删除用户',
    path: '/users/{user_id}',
    method: 'DELETE',
    auth_mode: 'app-key',
    scope: 'user:write',
    description: '软删除用户，需 user:write scope。',
    params: [{ name: 'user_id', location: 'path', required: true, type: 'number', description: '用户 ID' }],
    response_example: JSON.stringify(
      {
        code: 200,
        message: 'OK',
        data: { deleted: true },
        timestamp: '2026-10-03T12:00:00Z',
        request_id: 'req_open_xxxxx',
      },
      null,
      2,
    ),
    response_desc: '删除结果标记。',
  },
]

const modules = computed(() => {
  const map: Record<string, ApiDocEndpoint[]> = {}
  for (const d of STATIC_DOCS) {
    if (!map[d.module]) map[d.module] = []
    map[d.module].push(d)
  }
  return Object.entries(map).map(([name, items]) => ({ name, items }))
})

const METHOD_TAGS: Record<string, 'success' | 'warning' | 'primary' | 'info' | 'danger'> = {
  GET: 'success',
  POST: 'primary',
  PUT: 'warning',
  PATCH: 'warning',
  DELETE: 'danger',
}

function methodTagType(method: ApiDocEndpoint['method']): 'success' | 'warning' | 'primary' | 'info' | 'danger' {
  return METHOD_TAGS[method] || 'info'
}
</script>

<style scoped>
.docs-page {
  max-width: 1080px;
  margin: 0 auto;
}
.docs-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.sign-box {
  margin-top: 16px;
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
.sign-note {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.module-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.api-card {
  margin-bottom: 12px;
  border-radius: 12px;
  border: 1px solid #eef0f4;
}
.api-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.method-tag {
  font-weight: 600;
  min-width: 56px;
  text-align: center;
}
.api-path {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
}
.api-name {
  margin-left: auto;
  font-size: 13px;
  color: #909399;
}
.api-desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: #606266;
}
.empty-note {
  padding: 12px;
  font-size: 13px;
  color: #909399;
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
}
.resp-desc {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}
</style>
