<template>
  <div ref="wrapRef" class="gsearch">
    <div class="gsearch-input-wrap">
      <el-icon class="gsearch-icon"><Search /></el-icon>
      <input
        ref="inputRef"
        v-model="keyword"
        class="gsearch-input"
        type="text"
        placeholder="搜索功能模块、接口、应用…"
        @input="onInput"
        @focus="panelVisible = !!keyword.trim()"
        @keydown.enter.prevent="jumpFirst"
        @keydown.esc="closePanel"
      />
      <span v-if="!keyword" class="gsearch-kbd">/</span>
    </div>

    <div v-if="panelVisible" class="gsearch-panel" v-loading="loading">
      <template v-if="hasResults">
        <div v-for="group in visibleGroups" :key="group.key" class="gsearch-group">
          <div class="group-title">{{ group.label }}</div>
          <div
            v-for="item in group.items"
            :key="item.key"
            class="group-item"
            @mousedown.prevent="goTo(item)"
          >
            <div class="item-main">
              <span v-if="item.method" class="cap-method" :class="methodClass(item.method)">{{ item.method }}</span>
              <span class="item-name">{{ item.name }}</span>
            </div>
            <div class="item-sub">{{ item.sub }}</div>
          </div>
        </div>
        <div class="panel-footer" @mousedown.prevent="jumpFirst">在「{{ keyword }}」中查看全部结果</div>
      </template>
      <div v-else-if="!loading" class="gsearch-empty">未找到与 “{{ keyword }}” 相关的结果</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { capabilityModules } from '@/data/capability'
import type { CapabilityApi } from '@/types/capability'
import { listMyApps } from '@/api/apps'

const router = useRouter()
const wrapRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const keyword = ref('')
const loading = ref(false)
const panelVisible = ref(false)
const appHits = ref<SearchHit[]>([])

let debounceTimer: number | undefined
/** 请求序号：丢弃过期响应，避免快速输入时结果乱序覆盖 */
let searchSeq = 0

/** 搜索命中项（模块 / 接口 / 应用 统一结构） */
interface SearchHit {
  key: string
  name: string
  sub: string
  path: string
  method?: CapabilityApi['method']
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

/** 开放能力中的功能模块（如：用户管理、角色管理） */
function searchModules(kw: string): SearchHit[] {
  return capabilityModules
    .filter(m => m.name.includes(kw))
    .map(m => ({
      key: `mod:${m.key}`,
      name: m.name,
      sub: `${m.apis.length} 个开放接口`,
      path: `/capability/${m.key}`,
    }))
}

/** 开放能力中某一功能模块内的 API（如：创建用户、用户列表） */
function searchApis(kw: string): SearchHit[] {
  const upper = kw.toUpperCase()
  const hits: SearchHit[] = []
  for (const mod of capabilityModules) {
    for (const api of mod.apis) {
      if (api.name.includes(kw) || api.method === upper) {
        hits.push({
          key: `api:${mod.key}:${api.id}`,
          name: api.name,
          sub: `${mod.name} · ${api.method} ${api.path}`,
          path: `/capability/${mod.key}/${api.id}`,
          method: api.method,
        })
      }
    }
  }
  return hits
}

/** 应用管理中的应用（走后端：仅当前开发者名下的应用） */
async function searchApps(kw: string): Promise<SearchHit[]> {
  const res = await listMyApps({ page: 1, page_size: 5, keyword: kw })
  const items = res.data?.items ?? []
  return items.map(a => ({
    key: `app:${a.id}`,
    name: a.name,
    sub: a.app_id ?? '',
    path: `/apps?keyword=${encodeURIComponent(kw)}`,
  }))
}

const groups = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return []
  return [
    { key: 'modules', label: '功能模块', items: searchModules(kw) },
    { key: 'apis', label: '开放接口', items: searchApis(kw) },
    { key: 'apps', label: '应用', items: appHits.value },
  ].filter(g => g.items.length > 0)
})

const visibleGroups = computed(() => groups.value)
const hasResults = computed(() => visibleGroups.value.length > 0)

function onInput() {
  window.clearTimeout(debounceTimer)
  const kw = keyword.value.trim()
  if (!kw) {
    panelVisible.value = false
    appHits.value = []
    return
  }
  panelVisible.value = true
  debounceTimer = window.setTimeout(fetchApps, 300)
}

async function fetchApps() {
  const kw = keyword.value.trim()
  if (!kw) return
  const seq = ++searchSeq
  loading.value = true
  try {
    appHits.value = await searchApps(kw)
  } catch {
    if (seq === searchSeq) appHits.value = []
  } finally {
    if (seq === searchSeq) loading.value = false
  }
}

function goTo(item: SearchHit) {
  jumpTo(item.path)
}

/** Enter / 底部“查看全部”：跳转到首个有结果的分类 */
function jumpFirst() {
  const first = visibleGroups.value[0]
  if (first && first.items.length > 0) jumpTo(first.items[0].path)
}

function jumpTo(path: string) {
  const kw = keyword.value.trim()
  if (!kw) return
  router.push(path)
  keyword.value = ''
  appHits.value = []
  panelVisible.value = false
}

function closePanel() {
  panelVisible.value = false
  inputRef.value?.blur()
}

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)
}

function onGlobalKeydown(e: KeyboardEvent) {
  if (e.key === '/' && !isTypingTarget(e.target)) {
    e.preventDefault()
    inputRef.value?.focus()
    inputRef.value?.select()
  }
}

function onClickOutside(e: MouseEvent) {
  if (wrapRef.value && !wrapRef.value.contains(e.target as Node)) {
    panelVisible.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
  document.addEventListener('mousedown', onClickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  document.removeEventListener('mousedown', onClickOutside)
  window.clearTimeout(debounceTimer)
})
</script>

<style scoped>
.gsearch {
  position: relative;
  margin-right: 16px;
}

.gsearch-input-wrap {
  display: flex;
  align-items: center;
  width: 300px;
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--hj-border-lighter);
  border-radius: 10px;
  background: var(--hj-bg-page);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.gsearch-input-wrap:focus-within {
  border-color: var(--hj-primary);
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.gsearch-icon {
  color: var(--hj-text-secondary);
  font-size: 16px;
  margin-right: 8px;
  flex-shrink: 0;
}

.gsearch-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--hj-text-body);
}

.gsearch-input::placeholder {
  color: var(--hj-text-muted);
}

.gsearch-kbd {
  flex-shrink: 0;
  display: inline-block;
  padding: 0 7px;
  height: 22px;
  line-height: 20px;
  border: 1px solid var(--hj-border-lighter);
  border-radius: 5px;
  background: var(--hj-bg-card);
  color: var(--hj-text-secondary);
  font-size: 12px;
  font-family: inherit;
}

.gsearch-panel {
  position: absolute;
  top: 48px;
  right: 0;
  width: 380px;
  max-height: 480px;
  overflow-y: auto;
  background: var(--hj-bg-card);
  border: 1px solid var(--hj-border-lighter);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.14);
  z-index: 3000;
  padding: 6px 0;
}

.gsearch-group + .gsearch-group {
  border-top: 1px solid var(--hj-border-lighter);
}

.group-title {
  padding: 8px 14px 4px;
  font-size: 12px;
  color: var(--hj-text-secondary);
  font-weight: 600;
}

.group-item {
  padding: 7px 14px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.group-item:hover {
  background: var(--hj-bg-hover);
}

.item-main {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--hj-text-title);
  line-height: 1.4;
}

.item-sub {
  font-size: 12px;
  color: var(--hj-text-secondary);
  line-height: 1.4;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cap-method {
  display: inline-block;
  width: 34px;
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  line-height: 16px;
  border-radius: 3px;
}

.m-get { background: #67c23a; }
.m-post { background: var(--hj-primary); }
.m-patch { background: #e6a23c; }
.m-delete { background: #f56c6c; }

.panel-footer {
  padding: 8px 14px;
  border-top: 1px solid var(--hj-border-lighter);
  font-size: 12px;
  color: var(--hj-primary);
  cursor: pointer;
  text-align: center;
}

.panel-footer:hover {
  background: var(--hj-bg-hover);
}

.gsearch-empty {
  padding: 30px 16px;
  text-align: center;
  color: var(--hj-text-secondary);
  font-size: 13px;
}
</style>
