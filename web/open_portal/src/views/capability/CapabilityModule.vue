<template>
  <div class="capability-page">
    <!-- 模块头 -->
    <div class="module-head">
      <div class="crumbs">开放能力 / {{ module?.name ?? '接口文档' }}</div>
      <h1 class="module-title">{{ module?.name }}</h1>
      <p class="module-desc">{{ module?.desc }}</p>
    </div>

    <main v-if="currentApi" class="doc-main">
      <!-- 接口头部 -->
      <header class="api-hero">
        <div class="hero-method" :class="methodClass(currentApi.method)">{{ currentApi.method }}</div>
        <div class="hero-body">
          <div class="hero-title-row">
            <h2 class="hero-title">{{ currentApi.name }}</h2>
            <el-tag size="small" class="scope-tag" :type="currentApi.scope.startsWith('仅需') ? 'info' : 'warning'" effect="light">
              {{ currentApi.scope }}
            </el-tag>
          </div>
          <p class="hero-summary">{{ currentApi.summary }}</p>
          <code class="hero-path">{{ BASE }}{{ currentApi.path }}</code>
        </div>
      </header>

      <!-- API 说明 -->
      <section class="doc-section">
        <h3 class="section-title">API 说明</h3>
        <p class="api-summary">{{ currentApi.summary }}</p>
        <template v-if="currentApi.notes.length">
          <div class="sub-title">注意事项</div>
          <ul class="doc-list">
            <li v-for="(n, i) in currentApi.notes" :key="i">{{ n }}</li>
          </ul>
        </template>
        <template v-if="currentApi.limits.length">
          <div class="sub-title">使用限制</div>
          <ul class="doc-list">
            <li v-for="(l, i) in currentApi.limits" :key="i">{{ l }}</li>
          </ul>
        </template>
      </section>

      <!-- 请求说明 -->
      <section class="doc-section">
        <h3 class="section-title">请求说明</h3>
        <div class="meta-grid">
          <div class="meta-row">
            <span class="meta-label">请求地址</span>
            <code class="meta-value url-code">{{ BASE }}{{ currentApi.path }}</code>
          </div>
          <div class="meta-row">
            <span class="meta-label">HTTP 方法</span>
            <span class="meta-value">
              <span class="method-inline" :class="methodClass(currentApi.method)">{{ currentApi.method }}</span>
            </span>
          </div>
          <div class="meta-row">
            <span class="meta-label">签名方式</span>
            <span class="meta-value">HanJiang-1（HMAC-SHA256）</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">限频策略</span>
            <span class="meta-value">暂未启用（预留 429 限流）</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">权限要求</span>
            <span class="meta-value scope-text">{{ currentApi.scope }}</span>
          </div>
        </div>
      </section>

      <!-- 请求头 (Headers) -->
      <section class="doc-section">
        <h3 class="section-title">请求头 (Headers)</h3>
        <ParamTable :rows="currentApi.headers" name-label="Header 名称" />
      </section>

      <!-- 查询参数 (Query / Path) -->
      <section v-if="paramRows.length" class="doc-section">
        <h3 class="section-title">查询参数 (Query / Path)</h3>
        <ParamTable :rows="paramRows" name-label="属性名" show-loc />
      </section>

      <!-- 请求体 (Body) -->
      <section v-if="currentApi.body.length" class="doc-section">
        <h3 class="section-title">请求体 (Body)</h3>
        <ParamTable :rows="currentApi.body" name-label="属性名" />
      </section>

      <!-- 请求示例 -->
      <section class="doc-section">
        <h3 class="section-title">请求示例</h3>
        <div class="code-wrap">
          <div class="code-head">
            <span class="code-tab">cURL</span>
            <button class="copy-btn" @click="copy(currentApi.curl)">
              <el-icon :size="14"><CopyDocument /></el-icon>
              <span>{{ copied === currentApi.curl ? '已复制' : '复制' }}</span>
            </button>
          </div>
          <pre class="code-block">{{ currentApi.curl }}</pre>
        </div>
      </section>

      <!-- 响应体 (Response) -->
      <section class="doc-section">
        <h3 class="section-title">响应体 (Response)</h3>
        <ParamTable :rows="currentApi.responseFields" name-label="参数名称" />
      </section>

      <!-- 响应示例 -->
      <section class="doc-section">
        <h3 class="section-title">响应示例</h3>
        <div class="code-wrap">
          <div class="code-head">
            <span class="code-tab">JSON</span>
            <button class="copy-btn" @click="copy(currentApi.responseExample)">
              <el-icon :size="14"><CopyDocument /></el-icon>
              <span>{{ copied === currentApi.responseExample ? '已复制' : '复制' }}</span>
            </button>
          </div>
          <pre class="code-block">{{ currentApi.responseExample }}</pre>
        </div>
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

/** Query + Path 参数合并展示（Path 行带位置标记） */
const paramRows = computed(() => {
  const api = currentApi.value
  if (!api) return []
  return [
    ...api.query.map(r => ({ ...r, __loc: 'query' as const })),
    ...api.pathParams.map(r => ({ ...r, __loc: 'path' as const })),
  ]
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 4px 8px 24px;
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
.scope-tag {
  font-family: var(--hj-font-mono);
}
.hero-summary {
  margin: 8px 0 10px;
  font-size: 13.5px;
  color: var(--hj-text-regular);
  line-height: 1.7;
}
.hero-path,
.url-code {
  display: inline-block;
  font-family: var(--hj-font-mono);
  font-size: 13px;
  color: var(--hj-text-title);
  background: #fff;
  border: 1px solid var(--hj-primary-border);
  padding: 5px 12px;
  border-radius: 6px;
  word-break: break-all;
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
.api-summary {
  margin: 0 0 10px;
  font-size: 13.5px;
  color: var(--hj-text-regular);
  line-height: 1.8;
}
.sub-title {
  margin: 14px 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.doc-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13.5px;
  color: var(--hj-text-regular);
  line-height: 2;
}

/* ─── 请求说明 ─── */
.meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  border: 1px solid var(--hj-border-light);
  border-radius: 8px;
  overflow: hidden;
}
.meta-row {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--hj-border-lighter);
}
.meta-row:last-child {
  border-bottom: none;
}
.meta-label {
  flex-shrink: 0;
  width: 120px;
  font-size: 13px;
  color: var(--hj-text-secondary);
}
.meta-value {
  font-size: 13.5px;
  color: var(--hj-text-title);
  word-break: break-all;
}
.method-inline {
  display: inline-block;
  min-width: 52px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  line-height: 22px;
  border-radius: 4px;
  font-family: var(--hj-font-mono);
}
.scope-text {
  font-family: var(--hj-font-mono);
  font-size: 13px;
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  padding: 2px 10px;
  border-radius: 4px;
}

/* ─── 代码块（深色高亮主题，与认证文档页 CodeBlock 的 One Dark 风格一致） ─── */
.code-wrap {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #21252b;
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.08);
}
.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #21252b;
  border-bottom: 1px solid #2c323c;
  padding: 8px 14px;
}
.code-tab {
  font-size: 12.5px;
  font-weight: 600;
  color: #abb2bf;
  font-family: var(--hj-font-mono);
  letter-spacing: 0.5px;
}
.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #3a414d;
  background: transparent;
  color: #abb2bf;
  font-size: 12.5px;
  cursor: pointer;
  padding: 3px 10px;
  border-radius: 6px;
  transition: all 0.15s;
}
.copy-btn:hover {
  color: #e6e6e6;
  background: #2c323c;
  border-color: #4b5261;
}
.code-block {
  margin: 0;
  padding: 16px 20px;
  background: #282c34;
  font-family: var(--hj-font-mono);
  font-size: 12.5px;
  line-height: 1.8;
  color: #abb2bf;
  overflow-x: auto;
  user-select: text;
  white-space: pre;
}
.resp-desc {
  margin-top: 10px;
  font-size: 13px;
  color: var(--hj-text-secondary);
  line-height: 1.7;
}
</style>
