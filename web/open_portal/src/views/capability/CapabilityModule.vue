<template>
  <div class="capability-page">
    <!-- 模块头 -->
    <PageHead
      :crumbs="`开放能力 / ${module?.name ?? '接口文档'}`"
      :title="module?.name ?? '接口文档'"
      :desc="module?.desc ?? ''"
    />

    <main v-if="currentApi" class="doc-main">
      <!-- 页内锚点导航 -->
      <AuthAnchorNav :anchors="anchors" />

      <!-- 接口头部 -->
      <header class="api-hero">
        <div class="hero-method" :class="methodClass(currentApi.method)">{{ currentApi.method }}</div>
        <div class="hero-body">
          <div class="hero-title-row">
            <h2 class="hero-title">{{ currentApi.name }}</h2>
            <span class="scope-pill">
              <span class="scope-pill-label">权限</span>{{ currentApi.scope }}
            </span>
          </div>
          <p class="hero-summary">{{ currentApi.summary }}</p>
          <div class="hero-path-row">
            <code class="hero-path">{{ BASE }}{{ currentApi.path }}</code>
            <button class="path-copy" @click="copy(fullUrl)">
              <el-icon :size="13"><CopyDocument /></el-icon>
              <span>{{ copied === fullUrl ? '已复制' : '复制' }}</span>
            </button>
          </div>
        </div>
      </header>

      <!-- API 说明：三列信息卡 -->
      <section id="about" class="doc-section">
        <h3 class="section-title">API 说明</h3>
        <div class="info-grid">
          <div class="info-card info-main">
            <div class="info-card-title">接口说明</div>
            <div class="info-card-body">{{ currentApi.summary }}</div>
          </div>
          <div v-if="currentApi.notes.length" class="info-card info-note">
            <div class="info-card-title">注意事项</div>
            <ul class="info-card-list">
              <li v-for="(n, i) in currentApi.notes" :key="i">{{ n }}</li>
            </ul>
          </div>
          <div v-if="currentApi.limits.length" class="info-card info-limit">
            <div class="info-card-title">使用限制</div>
            <ul class="info-card-list">
              <li v-for="(l, i) in currentApi.limits" :key="i">{{ l }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 请求说明：端点摘要条 -->
      <section id="request-info" class="doc-section">
        <h3 class="section-title">请求说明</h3>
        <div class="endpoint-bar">
          <div class="endpoint-main">
            <span class="method-inline" :class="methodClass(currentApi.method)">{{ currentApi.method }}</span>
            <code class="endpoint-url">{{ BASE }}{{ currentApi.path }}</code>
            <button class="path-copy" @click="copy(fullUrl)">
              <el-icon :size="13"><CopyDocument /></el-icon>
              <span>{{ copied === fullUrl ? '已复制' : '复制' }}</span>
            </button>
          </div>
          <div class="endpoint-badges">
            <span class="ep-badge ep-sign">HanJiang-1 签名</span>
            <span class="ep-badge ep-limit">限流未启用</span>
            <span class="ep-badge ep-scope">scope：{{ currentApi.scope }}</span>
          </div>
        </div>
      </section>

      <!-- 请求头 (Headers) -->
      <section id="headers" class="doc-section">
        <h3 class="section-title">请求头 (Headers)</h3>
        <ParamTable :rows="currentApi.headers" name-label="Header 名称" />
      </section>

      <!-- 查询参数 (Query / Path) -->
      <section v-if="paramRows.length" id="query" class="doc-section">
        <h3 class="section-title">查询参数 (Query / Path)</h3>
        <ParamTable :rows="paramRows" name-label="属性名" show-loc />
      </section>

      <!-- 请求体 (Body) -->
      <section v-if="currentApi.body.length" id="body" class="doc-section">
        <h3 class="section-title">请求体 (Body)</h3>
        <ParamTable :rows="currentApi.body" name-label="属性名" />
      </section>

      <!-- 请求示例 -->
      <section id="request-example" class="doc-section">
        <h3 class="section-title">请求示例</h3>
        <CodeBlock :code="currentApi.curl" label="cURL" language="bash" />
      </section>

      <!-- 响应体 (Response) -->
      <section id="response-fields" class="doc-section">
        <h3 class="section-title">响应体 (Response)</h3>
        <ParamTable :rows="currentApi.responseFields" name-label="参数名称" />
      </section>

      <!-- 响应示例 -->
      <section id="response-example" class="doc-section">
        <h3 class="section-title">响应示例</h3>
        <CodeBlock :code="currentApi.responseExample" label="JSON" language="json" />
        <div class="resp-desc">{{ currentApi.responseDesc }}</div>
      </section>
    </main>

    <el-empty v-else description="该开放接口不存在或已下线，请从左侧菜单选择" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { capabilityModuleMap, BASE } from '@/data/capability'
import type { CapabilityApi, CapabilityModule } from '@/types/capability'
import ParamTable from './components/ParamTable.vue'
import CodeBlock from '@/components/CodeBlock.vue'
import PageHead from '@/components/PageHead.vue'
import AuthAnchorNav, { type AuthAnchor } from '@/components/AuthAnchorNav.vue'

const route = useRoute()

/** 当前模块（按 /capability/:module/:apiId 路由参数） */
const module = computed<CapabilityModule | undefined>(() => {
  const key = route.params.module as string
  return capabilityModuleMap[key as CapabilityModule['key']]
})

/** 当前接口（按 :apiId 路由参数驱动，支持三级菜单直达） */
const currentApi = computed<CapabilityApi | null>(() => {
  const id = route.params.apiId as string
  return module.value?.apis.find(a => a.id === id) ?? null
})

/** 完整请求地址（含域名） */
const fullUrl = computed(() => `${BASE}${currentApi.value?.path ?? ''}`)

/** Query + Path 参数合并展示（Path 行带位置标记） */
const paramRows = computed(() => {
  const api = currentApi.value
  if (!api) return []
  return [
    ...api.query.map(r => ({ ...r, __loc: 'query' as const })),
    ...api.pathParams.map(r => ({ ...r, __loc: 'path' as const })),
  ]
})

/** 页内锚点（按实际区块动态生成） */
const anchors = computed<AuthAnchor[]>(() => {
  const api = currentApi.value
  if (!api) return []
  const list: AuthAnchor[] = [
    { id: 'about', label: 'API 说明' },
    { id: 'request-info', label: '请求说明' },
    { id: 'headers', label: '请求头' },
  ]
  if (paramRows.value.length) list.push({ id: 'query', label: '查询参数' })
  if (api.body.length) list.push({ id: 'body', label: '请求体' })
  list.push({ id: 'request-example', label: '请求示例' })
  list.push({ id: 'response-fields', label: '响应体' })
  list.push({ id: 'response-example', label: '响应示例' })
  return list
})

/** 复制反馈（记录最近一次复制的文本，用于按钮文案切换） */
const copied = ref('')
async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = text
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => {
      if (copied.value === text) copied.value = ''
    }, 1600)
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
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
  /* 全宽铺满内容区，减少无用的空白 */
  padding: 4px 4px 24px;
}

/* ─── 模块头 ─── */
.module-head {
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--hj-border-light);
}
.crumbs {
  font-size: 12px;
  color: var(--hj-text-secondary);
  margin-bottom: 8px;
  letter-spacing: 0.3px;
}
.module-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--hj-text-title);
  letter-spacing: 0.5px;
}
.module-desc {
  margin: 0;
  font-size: 13px;
  color: var(--hj-text-secondary);
  line-height: 1.7;
}

/* ─── 接口头部 ─── */
.api-hero {
  display: flex;
  gap: 18px;
  align-items: flex-start;
  background: linear-gradient(135deg, #ffffff 0%, #f5f9ff 100%);
  border: 1px solid var(--hj-primary-border);
  border-radius: var(--hj-radius-lg);
  padding: 24px 28px;
  margin-bottom: 20px;
  box-shadow: var(--hj-shadow-card);
}
.hero-method {
  flex-shrink: 0;
  min-width: 64px;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  line-height: 34px;
  border-radius: 8px;
  letter-spacing: 1px;
  font-family: var(--hj-font-mono);
}
.m-get { background: linear-gradient(135deg, #67c23a, #4da32b); }
.m-post { background: linear-gradient(135deg, #409eff, #2b7de0); }
.m-patch { background: linear-gradient(135deg, #e6a23c, #d08a1e); }
.m-delete { background: linear-gradient(135deg, #f56c6c, #e54848); }
.hero-body {
  flex: 1;
  min-width: 0;
}
.hero-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.hero-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--hj-text-title);
}
.scope-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--hj-font-mono);
  font-size: 12px;
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  border: 1px solid var(--hj-primary-border);
  padding: 2px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.scope-pill-label {
  font-size: 11px;
  color: var(--hj-text-muted);
  font-family: inherit;
}
.hero-summary {
  margin: 8px 0 10px;
  font-size: 13.5px;
  color: var(--hj-text-regular);
  line-height: 1.7;
}
.hero-path-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid var(--hj-primary-border);
  border-radius: 8px;
  padding: 5px 8px 5px 12px;
}
.hero-path {
  font-family: var(--hj-font-mono);
  font-size: 13px;
  color: var(--hj-text-title);
  word-break: break-all;
}
.path-copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--hj-primary-border);
  background: var(--hj-primary-bg);
  color: var(--hj-primary);
  font-size: 12px;
  cursor: pointer;
  padding: 3px 10px;
  border-radius: 6px;
  transition: all 0.15s;
  flex-shrink: 0;
}
.path-copy:hover {
  background: var(--hj-primary);
  color: #fff;
  border-color: var(--hj-primary);
}

/* ─── 区块卡片 ─── */
.doc-section {
  background: var(--hj-bg-card);
  border: 1px solid var(--hj-border-light);
  border-radius: var(--hj-radius-lg);
  padding: 22px 26px;
  margin-bottom: 18px;
  box-shadow: var(--hj-shadow-card);
}
.section-title {
  position: relative;
  margin: 0 0 18px;
  padding-left: 12px;
  font-size: 16px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 2px;
  width: 4px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--hj-primary), var(--hj-primary-weak));
}

/* ─── API 说明：三列信息卡 ─── */
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.info-card {
  border-radius: 10px;
  padding: 14px 16px;
}
.info-main {
  background: var(--hj-bg-page);
  border: 1px solid var(--hj-border-light);
}
.info-note {
  background: #fff8f0;
  border: 1px solid #f3d9b5;
}
.info-limit {
  background: #f0f7ff;
  border: 1px solid #bcd7f5;
}
.info-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.info-main .info-card-title { color: var(--hj-text-title); }
.info-note .info-card-title { color: #b45309; }
.info-limit .info-card-title { color: #1d4ed8; }
.info-card-body {
  font-size: 13px;
  color: var(--hj-text-regular);
  line-height: 1.75;
}
.info-card-list {
  margin: 0;
  padding-left: 16px;
  font-size: 12.5px;
  color: var(--hj-text-regular);
  line-height: 1.85;
}

/* ─── 请求说明：端点摘要条 ─── */
.endpoint-bar {
  border: 1px solid var(--hj-border-light);
  border-radius: 10px;
  overflow: hidden;
  background: var(--hj-bg-page);
}
.endpoint-main {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  flex-wrap: wrap;
}
.method-inline {
  display: inline-block;
  min-width: 58px;
  text-align: center;
  font-size: 12.5px;
  font-weight: 700;
  color: #fff;
  line-height: 26px;
  border-radius: 6px;
  font-family: var(--hj-font-mono);
}
.endpoint-url {
  flex: 1;
  min-width: 0;
  font-family: var(--hj-font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--hj-text-title);
  word-break: break-all;
}
.endpoint-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 18px 14px;
}
.ep-badge {
  display: inline-block;
  font-size: 12px;
  line-height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.ep-sign {
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  border: 1px solid var(--hj-primary-border);
}
.ep-limit {
  color: #6b7280;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}
.ep-scope {
  color: #7c3aed;
  background: #f6f4fe;
  border: 1px solid #e4d9f7;
  font-family: var(--hj-font-mono);
}

.resp-desc {
  margin-top: 12px;
  font-size: 13px;
  color: var(--hj-text-secondary);
  line-height: 1.7;
}
</style>
