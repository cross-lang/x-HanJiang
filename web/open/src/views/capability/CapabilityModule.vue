<template>
  <div class="capability-page">
    <div class="capability-layout">
      <!-- 左侧：接口目录（模块内接口列表） -->
      <aside class="doc-nav">
        <div class="nav-head">
          <div class="nav-module">{{ module?.name }}</div>
          <div class="nav-desc">{{ module?.desc }}</div>
        </div>
        <div class="nav-list">
          <div
            v-for="api in module?.apis"
            :key="api.id"
            class="nav-item"
            :class="{ active: api.id === currentApi?.id }"
            @click="currentApi = api"
          >
            <span class="nav-method" :class="methodClass(api.method)">{{ api.method }}</span>
            <span class="nav-name">{{ api.name }}</span>
          </div>
        </div>
      </aside>

      <!-- 右侧：接口详情 -->
      <main v-if="currentApi" class="doc-main">
        <!-- 标题 -->
        <div class="api-head">
          <h2 class="api-name">{{ currentApi.name }}</h2>
          <div class="api-path-line">
            <el-tag :type="methodTagType(currentApi.method)" size="small" class="method-tag">{{ currentApi.method }}</el-tag>
            <code class="api-path">/api/open/v1{{ currentApi.path }}</code>
            <el-tag size="small" class="hj-ml-8" :type="currentApi.scope.startsWith('仅需') ? 'info' : 'warning'">
              {{ currentApi.scope }}
            </el-tag>
          </div>
        </div>

        <!-- API 说明 -->
        <section class="doc-section">
          <h3 class="section-title">API 说明</h3>
          <p class="api-summary">{{ currentApi.summary }}</p>
          <template v-if="currentApi.notes.length">
            <div class="sub-title">注意事项：</div>
            <ul class="doc-list">
              <li v-for="(n, i) in currentApi.notes" :key="i">{{ n }}</li>
            </ul>
          </template>
          <template v-if="currentApi.limits.length">
            <div class="sub-title">使用限制：</div>
            <ul class="doc-list">
              <li v-for="(l, i) in currentApi.limits" :key="i">{{ l }}</li>
            </ul>
          </template>
        </section>

        <!-- 请求说明 -->
        <section class="doc-section">
          <h3 class="section-title">请求说明</h3>
          <el-table :data="requestMeta" border size="small">
            <el-table-column prop="field" label="字段" width="110" />
            <el-table-column prop="value" label="值" />
          </el-table>
        </section>

        <!-- 请求头 (Headers) -->
        <section class="doc-section">
          <h3 class="section-title">请求头 (Headers)</h3>
          <el-table :data="currentApi.headers" border size="small">
            <el-table-column prop="name" label="Header 名称" width="200" />
            <el-table-column prop="type" label="参数类型" width="100" />
            <el-table-column label="是否必填" width="90">
              <template #default="{ row }">
                <el-tag :type="row.required ? 'danger' : 'info'" size="small">{{ row.required ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="values" label="可选值" width="130" />
            <el-table-column prop="limit" label="限制" width="180" />
            <el-table-column prop="example" label="示例" width="220" />
            <el-table-column prop="desc" label="描述" min-width="220" />
          </el-table>
        </section>

        <!-- 查询参数 (Query / Path) -->
        <section v-if="currentApi.query.length || currentApi.pathParams.length" class="doc-section">
          <h3 class="section-title">查询参数 (Query / Path)</h3>
          <el-table :data="paramRows" border size="small">
            <el-table-column label="位置" width="70">
              <template #default="{ row }">
                <el-tag size="small" :type="row.__loc === 'path' ? 'warning' : 'primary'">{{ row.__loc }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="属性名" width="180" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column label="是否必填" width="90">
              <template #default="{ row }">
                <el-tag :type="row.required ? 'danger' : 'info'" size="small">{{ row.required ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="values" label="可选值" width="150" />
            <el-table-column prop="limit" label="限制" width="150" />
            <el-table-column prop="example" label="示例" width="180" />
            <el-table-column prop="desc" label="描述" min-width="220" />
          </el-table>
        </section>

        <!-- 请求体 (Body) -->
        <section v-if="currentApi.body.length" class="doc-section">
          <h3 class="section-title">请求体 (Body)</h3>
          <el-table :data="currentApi.body" border size="small">
            <el-table-column prop="name" label="属性名" width="180" />
            <el-table-column prop="type" label="类型" width="130" />
            <el-table-column label="是否必填" width="90">
              <template #default="{ row }">
                <el-tag :type="row.required ? 'danger' : 'info'" size="small">{{ row.required ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="values" label="可选值" width="150" />
            <el-table-column prop="limit" label="限制" width="150" />
            <el-table-column prop="example" label="示例" width="180" />
            <el-table-column prop="desc" label="描述" min-width="220" />
          </el-table>
        </section>

        <!-- 请求示例 -->
        <section class="doc-section">
          <h3 class="section-title">请求示例</h3>
          <div class="curl-tab">cURL</div>
          <pre class="code-block">{{ currentApi.curl }}</pre>
        </section>

        <!-- 响应体 (Response) -->
        <section class="doc-section">
          <h3 class="section-title">响应体 (Response)</h3>
          <el-table :data="currentApi.responseFields" border size="small">
            <el-table-column prop="name" label="参数名称" width="220" />
            <el-table-column prop="type" label="参数类型" width="130" />
            <el-table-column prop="values" label="可选值" width="140" />
            <el-table-column prop="limit" label="限制" width="140" />
            <el-table-column prop="example" label="示例" width="200" />
            <el-table-column prop="desc" label="描述" min-width="220" />
          </el-table>
        </section>

        <!-- 响应示例 -->
        <section class="doc-section">
          <h3 class="section-title">响应示例</h3>
          <pre class="code-block">{{ currentApi.responseExample }}</pre>
          <div class="resp-desc">{{ currentApi.responseDesc }}</div>
        </section>
      </main>

      <el-empty v-else description="该模块暂无开放接口" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { capabilityModuleMap } from '@/data/capability'
import type { CapabilityApi, CapabilityModule } from '@/types/capability'

const route = useRoute()

/** 当前模块（按 /capability/:module 路由参数） */
const module = computed<CapabilityModule | undefined>(() => {
  const key = route.params.module as string
  return capabilityModuleMap[key as CapabilityModule['key']]
})

/** 当前选中接口（默认模块第一个；路由参数变化时重置） */
const currentApi = ref<CapabilityApi | null>(null)

watch(
  module,
  m => {
    currentApi.value = m?.apis[0] ?? null
  },
  { immediate: true },
)

/** 请求说明（请求地址 / HTTP方法 / 签名方式 / 限频策略 / 权限要求） */
const requestMeta = computed(() => [
  { field: '请求地址', value: `http://127.0.0.1:8000/api/open/v1${currentApi.value?.path}` },
  { field: 'HTTP 方法', value: currentApi.value?.method ?? '-' },
  { field: '签名方式', value: 'HanJiang-1（HMAC-SHA256）' },
  { field: '限频策略', value: '暂未启用（预留 429 限流）' },
  { field: '权限要求', value: currentApi.value?.scope ?? '-' },
])

/** Query + Path 参数合并展示（Path 行带位置标记） */
const paramRows = computed(() => {
  const api = currentApi.value
  if (!api) return []
  const rows = [
    ...api.query.map(r => ({ ...r, __loc: 'query' as const })),
    ...api.pathParams.map(r => ({ ...r, __loc: 'path' as const })),
  ]
  return rows
})

const METHOD_TAGS: Record<CapabilityApi['method'], 'success' | 'warning' | 'primary' | 'info' | 'danger'> = {
  GET: 'success',
  POST: 'primary',
  PATCH: 'warning',
  DELETE: 'danger',
}

function methodTagType(method: CapabilityApi['method']): 'success' | 'warning' | 'primary' | 'info' | 'danger' {
  return METHOD_TAGS[method] || 'info'
}

const METHOD_CLASS: Record<CapabilityApi['method'], string> = {
  GET: 'm-get',
  POST: 'm-post',
  PATCH: 'm-patch',
  DELETE: 'm-delete',
}

function methodClass(method: CapabilityApi['method']): string {
  return METHOD_CLASS[method]
}
</script>

<style scoped>
.capability-page {
  max-width: 1240px;
  margin: 0 auto;
}
.capability-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
/* 左侧目录 */
.doc-nav {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  overflow: hidden;
  position: sticky;
  top: 0;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}
.nav-head {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f2f5;
}
.nav-module {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.nav-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
.nav-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.nav-item:hover {
  background: #f5f7fa;
}
.nav-item.active {
  background: #ecf5ff;
}
.nav-method {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  color: #fff;
  flex-shrink: 0;
}
.m-get { background: #67c23a; }
.m-post { background: #409eff; }
.m-patch { background: #e6a23c; }
.m-delete { background: #f56c6c; }
.nav-name {
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
}
.nav-item.active .nav-name {
  color: #409eff;
  font-weight: 500;
}
/* 右侧详情 */
.doc-main {
  flex: 1;
  min-width: 0;
}
.api-head {
  margin-bottom: 12px;
}
.api-name {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}
.api-path-line {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.method-tag {
  font-weight: 600;
  min-width: 56px;
  text-align: center;
}
.api-path {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
}
.hj-ml-8 {
  margin-left: 8px;
}
.doc-section {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 16px;
}
.section-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.api-summary {
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}
.sub-title {
  margin: 8px 0 4px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}
.doc-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #606266;
  line-height: 1.9;
}
.curl-tab {
  display: inline-block;
  margin-bottom: 10px;
  padding: 4px 14px;
  border-radius: 6px 6px 0 0;
  background: #303133;
  color: #fff;
  font-size: 13px;
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
.resp-desc {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}
</style>
